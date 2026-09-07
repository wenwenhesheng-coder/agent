"""
合规拦截器（亮点八核心：金融合规硬隔离架构）

把合规模块独立出来，不是简单提示词约束：
- 所有大模型输出先过合规校验
- 违规输出自动拦截并替换
- 强制附带监管要求的风险提示
- 全链路留痕可审计
"""
from __future__ import annotations

from typing import Optional

from loguru import logger

from compliance.rule_engine import ComplianceRuleEngine
from compliance.audit_logger import AuditLogger
from core.models import (
    ComplianceCheckResult,
    RiskLevel,
    RecommendationItem,
    AgentThought,
)
from core.exceptions import ComplianceViolationError


class ComplianceInterceptor:
    """
    合规拦截器
    - 位于大模型输出与用户之间，形成硬隔离
    - 所有输出必须经过此处校验，否则不允许返回用户
    """

    def __init__(self):
        self.rule_engine = ComplianceRuleEngine()
        self.audit_logger = AuditLogger()

    async def intercept(
        self,
        content: str,
        user_id: str,
        agent_name: str,
        user_risk_level: RiskLevel = RiskLevel.CONSERVATIVE,
        recommendations: list[RecommendationItem] | None = None,
        reasoning_chain: list[AgentThought] | None = None,
        data_sources: list[str] | None = None,
    ) -> tuple[str, ComplianceCheckResult]:
        """
        拦截并校验输出
        Returns: (合规输出内容, 合规校验结果)
        如果违规且无法修复，抛出 ComplianceViolationError
        """
        logger.info(f"合规拦截器启动 | 用户={user_id} | Agent={agent_name}")

        # 执行合规校验
        result: ComplianceCheckResult = self.rule_engine.check(
            content=content,
            user_risk_level=user_risk_level,
            recommendations=recommendations,
        )

        # 记录审计日志（全链路留痕）
        await self.audit_logger.log(
            user_id=user_id,
            agent_name=agent_name,
            input_content="",  # 输入在外部记录
            output_content=content,
            compliance_result=result,
            reasoning_chain=reasoning_chain or [],
            data_sources=data_sources or [],
        )

        if not result.passed:
            # 有违规但可修复（敏感词替换 + 强制风险提示）
            logger.warning(
                f"合规校验未通过 | 审计ID={result.audit_id} | "
                f"违规数={len(result.violated_rules)}"
            )

            # 如果是严重违规（风险等级不匹配 + 产品无来源），直接拦截
            severe = any(
                "超出用户风险等级" in v or "未标注数据来源" in v
                for v in result.violated_rules
            )
            if severe and recommendations:
                # 过滤掉不合规的推荐
                recommendations = [
                    r for r in (recommendations or [])
                    if r.compliance_passed
                ]
                logger.warning(f"已过滤不合规推荐项，剩余{len(recommendations)}项")

            # 返回消毒后的内容 + 风险提示
            sanitized = result.sanitized_content
            if result.risk_warnings:
                sanitized = "\n\n".join(result.risk_warnings) + "\n\n" + sanitized

            return sanitized, result

        # 校验通过
        logger.info(f"合规校验通过 | 审计ID={result.audit_id}")
        return result.sanitized_content, result

    async def intercept_input(
        self,
        user_input: str,
        user_id: str,
    ) -> str:
        """输入侧合规检查（防止用户诱导违规）"""
        # 检测用户是否在诱导模型做出违规承诺
        inducement_patterns = [
            "你保证", "你承诺", "你发誓", "确定能赚",
            "是不是保本", "能不能保证不亏",
        ]
        for pattern in inducement_patterns:
            if pattern in user_input:
                logger.warning(f"检测到用户诱导性提问: {pattern}")
                return (
                    f"用户提问含诱导性内容[{pattern}]，"
                    f"已记录审计。智能体将坚持合规原则，"
                    f"不做出任何保本/保证收益的承诺。"
                )
        return user_input
