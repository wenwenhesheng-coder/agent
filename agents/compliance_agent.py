"""
合规审查Agent（亮点一 + 亮点七、八）

内嵌合规规则引擎，对每一条建议进行合规校验。
这是独立一层，不是简单提示词约束。
"""
from __future__ import annotations

from loguru import logger

from agents.base_agent import BaseAgent
from core.models import (
    RiskLevel, RecommendationItem, ComplianceCheckResult, AgentThought,
)
from compliance.interceptor import ComplianceInterceptor


class ComplianceAgent(BaseAgent):
    name = "compliance_agent"
    role = "合规审查Agent"
    description = "内嵌合规规则引擎，对每一条建议进行合规校验拦截"

    def __init__(self, memory_engine, retriever=None):
        super().__init__(memory_engine, retriever)
        self.interceptor = ComplianceInterceptor()

    def get_system_prompt(self) -> str:
        return (
            "你是银行理财顾问智能体的「合规审查Agent」。\n"
            "职责：\n"
            "1. 对所有Agent输出进行合规校验（独立规则引擎，非提示词约束）\n"
            "2. 拦截违规话术：保本承诺、保证收益、敏感词等\n"
            "3. 校验推荐产品风险等级是否匹配用户风险等级\n"
            "4. 强制附加风险提示语\n"
            "5. 全链路操作留痕，满足金融监管审计要求\n\n"
            "合规红线（绝对禁止）：\n"
            "- 禁止承诺保本、保证收益、刚性兑付\n"
            "- 禁止推荐超出用户风险等级的产品\n"
            "- 禁止使用诱导性话术\n"
            "- 禁止提及内幕信息\n"
            "- 所有输出须附带风险提示\n\n"
            "你是银行最关心的合规防线，必须严格独立执行。"
        )

    async def review(
        self,
        user_id: str,
        content: str,
        risk_level: RiskLevel = RiskLevel.CONSERVATIVE,
        recommendations: list[RecommendationItem] | None = None,
        data_sources: list[str] | None = None,
    ) -> tuple[str, ComplianceCheckResult]:
        """
        合规审查
        Returns: (合规后内容, 合规校验结果)
        """
        logger.info(f"合规审查Agent启动审查 | 内容长度={len(content)}")

        sanitized, result = await self.interceptor.intercept(
            content=content,
            user_id=user_id,
            agent_name=self.name,
            user_risk_level=risk_level,
            recommendations=recommendations,
            reasoning_chain=self.thoughts,
            data_sources=data_sources,
        )

        self.thoughts.append(AgentThought(
            agent_name=self.name,
            thought=(
                f"合规校验{'通过' if result.passed else '拦截'}"
                f"{'，违规'+str(len(result.violated_rules))+'项' if not result.passed else ''}"
            ),
            action="compliance_rule_engine_check",
            observation=f"audit_id={result.audit_id}, passed={result.passed}",
        ))
        return sanitized, result
