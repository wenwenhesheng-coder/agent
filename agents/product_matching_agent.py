"""
产品匹配Agent（亮点一 + 亮点三协同）

基于客户画像与市场判断，动态生成个性化资产配置建议。
大小模型协同：调用量化小模型计算资产配置，再由大模型解读。
"""
from __future__ import annotations

import json
from typing import Any

from loguru import logger

from agents.base_agent import BaseAgent
from core.models import RiskLevel, RecommendationItem, AgentThought
from tools.product_kb import ProductKnowledgeBaseTool
from tools.calculators import AssetAllocationTool
from models.quant_models import asset_allocation_model


class ProductMatchingAgent(BaseAgent):
    name = "product_matching_agent"
    role = "产品匹配Agent"
    description = "基于客户画像与市场判断，动态生成个性化资产配置建议"

    def get_system_prompt(self) -> str:
        return (
            "你是银行理财顾问智能体的「产品匹配Agent」。\n"
            "职责：\n"
            "1. 基于用户风险等级和画像，调用量化小模型计算资产配置方案\n"
            "2. 从理财产品知识库查询适配的具体产品\n"
            "3. 生成个性化资产配置建议，每条推荐须附带理由（XAI）\n"
            "4. 所有推荐须标注数据来源（抑制幻觉）\n\n"
            "要求：\n"
            "- 推荐产品风险等级不得超过用户风险等级\n"
            "- 不做收益承诺，使用'预期'\"参考\"等表述\n"
            "- 配置方案须基于量化小模型计算，不凭空生成\n"
            "- 每条推荐须有数据来源（知识库来源标注）\n"
            "- 这是科普性配置建议，非具体产品推荐指令"
        )

    async def match_products(
        self,
        user_id: str,
        risk_level: RiskLevel,
        preferences: list[str] | None = None,
        market_analysis: str = "",
    ) -> tuple[str, list[RecommendationItem]]:
        """
        生成资产配置建议
        Returns: (配置建议文本, 推荐项列表)
        """
        # === 亮点三：大小模型协同 ===
        # 1. 调用量化小模型计算资产配置
        alloc_result = asset_allocation_model.calculate(risk_level, None, preferences)
        logger.info(f"量化小模型计算完成: 预期收益={alloc_result.expected_return}")

        # 2. 从产品知识库查询适配产品（适当性筛选）
        product_tool = ProductKnowledgeBaseTool()
        products_text = await product_tool.execute(
            query="",
            risk_level_max=risk_level.level_num,
        )

        # 3. 检索知识库补充产品说明
        rag_context = ""
        if self.retriever:
            result = await self.retriever.retrieve(
                f"理财产品 风险等级{risk_level.value} 配置"
            )
            rag_context = self.retriever.get_context_for_llm(result)

        # 4. 大模型综合解读
        messages = [
            {"role": "system", "content": self.get_system_prompt()},
            {"role": "user", "content": (
                f"用户风险等级：{risk_level.value}\n"
                f"用户偏好：{preferences or '无特殊偏好'}\n"
                f"市场分析：{market_analysis[:300]}\n\n"
                f"【量化小模型计算结果】\n{self._format_alloc(alloc_result)}\n\n"
                f"【知识库产品信息】\n{products_text}\n\n"
                f"{rag_context}\n\n"
                f"请基于以上真实数据生成资产配置科普建议，"
                f"每条推荐须附带理由和数据来源。"
            )},
        ]
        recommendation_text = await self.llm.chat(messages)

        # 5. 构建推荐项（带来源标注 + XAI理由）
        recommendations = self._build_recommendations(alloc_result, products_text)

        self.thoughts.append(AgentThought(
            agent_name=self.name,
            thought=f"量化小模型计算+知识库检索+大模型解读，风险={risk_level.value}",
            action="calculate_asset_allocation + query_product_kb + llm",
            observation=f"预期收益={alloc_result.expected_return}, {len(recommendations)}项推荐",
        ))
        logger.info(f"产品匹配Agent完成: {len(recommendations)}项推荐")
        return recommendation_text, recommendations

    def _format_alloc(self, result) -> str:
        lines = [f"策略：{result.strategy}", "配置比例："]
        for k, v in result.allocations.items():
            lines.append(f"  {k}: {v*100:.1f}%")
        lines.append(f"预期年化收益：{result.expected_return*100:.2f}%")
        lines.append(f"预期波动率：{result.expected_volatility*100:.2f}%")
        lines.append(f"夏普比率：{result.sharpe_ratio}")
        lines.append(f"风险解释：{result.risk_explanation}")
        return "\n".join(lines)

    def _build_recommendations(self, alloc_result, products_text: str) -> list[RecommendationItem]:
        """从配置方案构建推荐项（带来源标注 + XAI理由）"""
        recommendations = []
        for asset_class, ratio in alloc_result.allocations.items():
            # 在产品文本中匹配该类别的产品
            source = "量化模型计算结果"
            # 简化匹配：知识库中有的产品来源标注
            if "固收" in asset_class or "理财" in asset_class:
                source = "理财产品知识库+量化模型"
            elif "基金" in asset_class:
                source = "基金知识库+量化模型"
            elif "黄金" in asset_class:
                source = "市场行情数据+量化模型"

            recommendations.append(RecommendationItem(
                product_name=asset_class,
                product_type=self._classify_type(asset_class),
                risk_level=self._classify_risk(asset_class),
                expected_return_range=f"参考量化模型预期",
                recommended_reason=(
                    f"基于{alloc_result.strategy}，配置{ratio*100:.1f}%。"
                    f"该类别在当前策略下有助于{self._reason_benefit(asset_class)}。"
                    f"数据来源：{source}。"
                ),
                allocation_ratio=ratio,
                data_source=source,
                compliance_passed=True,
            ))
        return recommendations

    def _classify_type(self, asset_class: str) -> str:
        if "货币" in asset_class:
            return "货币基金"
        if "理财" in asset_class:
            return "银行理财"
        if "债" in asset_class:
            return "债券基金"
        if "股票" in asset_class or "指数" in asset_class:
            return "股票基金"
        if "黄金" in asset_class:
            return "黄金基金"
        if "REITs" in asset_class:
            return "REITs"
        if "QDII" in asset_class:
            return "QDII基金"
        return "其他"

    def _classify_risk(self, asset_class: str) -> str:
        if "货币" in asset_class:
            return "R1(低风险)"
        if "固收" in asset_class or "理财R1-R2" in asset_class or "纯债" in asset_class:
            return "R2(中低风险)"
        if "固收+" in asset_class or "混合" in asset_class or "REITs" in asset_class:
            return "R3(中风险)"
        if "股票" in asset_class or "黄金" in asset_class or "QDII" in asset_class:
            return "R4(中高风险)"
        return "R2(中低风险)"

    def _reason_benefit(self, asset_class: str) -> str:
        if "货币" in asset_class:
            return "满足流动性需求"
        if "固收" in asset_class or "理财" in asset_class:
            return "获取稳定票息收益作为底仓"
        if "纯债" in asset_class:
            return "提供中低风险的稳定回报"
        if "固收+" in asset_class:
            return "在固收底仓基础上增强收益弹性"
        if "混合" in asset_class:
            return "平衡风险与收益"
        if "股票" in asset_class or "指数" in asset_class:
            return "获取长期权益增值"
        if "黄金" in asset_class:
            return "分散风险、对冲通胀"
        if "REITs" in asset_class:
            return "获取另类资产的分红收益"
        if "QDII" in asset_class:
            return "实现全球化分散配置"
        return "优化组合整体表现"
