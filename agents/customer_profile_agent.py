"""
客户画像Agent（亮点一）

整合客户行为数据、交易记录、风险测评等多维信息，
构建动态精准用户画像。
"""
from __future__ import annotations

from loguru import logger

from agents.base_agent import BaseAgent
from core.models import RiskLevel, AgentThought
from memory.user_profile import UserProfileManager
from data.user_data_adapter import user_data_adapter


class CustomerProfileAgent(BaseAgent):
    name = "customer_profile_agent"
    role = "客户画像Agent"
    description = "整合客户多维信息，构建动态精准用户画像"

    def get_system_prompt(self) -> str:
        return (
            "你是银行理财顾问智能体的「客户画像Agent」。\n"
            "职责：\n"
            "1. 从用户对话中提取画像信息（风险等级、收入区间、偏好、认知水平）\n"
            "2. 整合用户行为数据、交易记录、风险测评结果\n"
            "3. 构建用户投资风格画像 + 认知水平画像\n"
            "4. 将画像信息传递给后续Agent使用\n\n"
            "要求：\n"
            "- 只使用脱敏后的数据，不接触敏感资产数据\n"
            "- 用户画像须基于对话和已知信息动态更新\n"
            "- 输出简洁的画像摘要，供其他Agent参考\n"
            "- 严格遵守数据安全要求，不记录敏感信息"
        )

    async def build_profile(self, user_id: str, user_input: str) -> str:
        """
        构建/更新用户画像
        Returns: 画像摘要文本
        """
        # 1. 从银行系统获取脱敏后的基础画像
        bank_profile = user_data_adapter.get_user_profile(user_id)
        # 2. 从对话中提取额外信息
        profile_manager = UserProfileManager(self.memory)
        extracted = profile_manager.extract_from_message(user_id, user_input)

        # 3. 合并画像（优先使用银行系统的风险等级）
        ltm = self.memory.get_long_term(user_id)
        bank_risk = bank_profile.get("risk_level", "保守型")
        # 优先使用银行系统画像中的风险等级
        risk_level_str = bank_risk
        # 更新长期记忆中的风险等级
        self.memory.update_profile(user_id, risk_level=risk_level_str)
        try:
            risk_level = RiskLevel(risk_level_str)
        except ValueError:
            risk_level = RiskLevel.CONSERVATIVE

        # 4. 生成画像摘要
        summary = self.memory.get_profile_summary(user_id)
        bank_info = (
            f"银行系统画像：风险等级={bank_profile.get('risk_level')}, "
            f"认知水平={bank_profile.get('knowledge_level')}, "
            f"持有产品={bank_profile.get('holding_products', [])}"
        )

        result = f"{summary}\n{bank_info}\n\n画像Agent结论：用户为「{risk_level.value}」投资者"
        if extracted:
            result += f"，本轮新提取信息：{extracted}"
        result += "。"

        logger.info(f"客户画像Agent完成画像构建: risk={risk_level.value}")
        self.thoughts.append(AgentThought(
            agent_name=self.name,
            thought=f"构建用户画像: {risk_level.value}, 提取信息: {extracted}",
            observation=result[:200],
        ))
        return result
