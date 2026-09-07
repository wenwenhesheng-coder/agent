"""
多智能体协调器（亮点一核心）

编排多个专业Agent协同作业，形成从需求识别到方案输出的完整作战单元。
规划拆解：把用户复杂理财问题拆解为多步执行。
"""
from __future__ import annotations

import re
from typing import Any

from loguru import logger

from config.settings import settings
from core.models import (
    AgentThought, RiskLevel, RecommendationItem,
    ComplianceCheckResult, WealthPlan,
)
from agents.base_agent import BaseAgent
from agents.customer_profile_agent import CustomerProfileAgent
from agents.market_analysis_agent import MarketAnalysisAgent
from agents.product_matching_agent import ProductMatchingAgent
from agents.compliance_agent import ComplianceAgent
from agents.dialogue_agent import DialogueAgent
from memory.memory_engine import MemoryEngine
from rag.retriever import AgenticRetriever
from data.user_data_adapter import user_data_adapter


class AgentOrchestrator:
    """
    多智能体协调器
    - 规划拆解用户问题
    - 调度多个Agent协同执行
    - 合规风控拦截
    - 生成推理链（XAI）
    """

    def __init__(
        self,
        memory_engine: MemoryEngine,
        retriever: AgenticRetriever,
    ):
        self.memory = memory_engine
        self.retriever = retriever

        # 初始化5个专业Agent
        self.profile_agent = CustomerProfileAgent(memory_engine, retriever)
        self.market_agent = MarketAnalysisAgent(memory_engine, retriever)
        self.product_agent = ProductMatchingAgent(memory_engine, retriever)
        self.compliance_agent = ComplianceAgent(memory_engine, retriever)
        self.dialogue_agent = DialogueAgent(memory_engine, retriever)

        # Agent注册表
        self.agents: dict[str, BaseAgent] = {
            "customer_profile": self.profile_agent,
            "market_analysis": self.market_agent,
            "product_matching": self.product_agent,
            "compliance": self.compliance_agent,
            "dialogue": self.dialogue_agent,
        }
        logger.info(f"多智能体协调器已初始化: {list(self.agents.keys())}")

    def plan(self, user_input: str) -> list[str]:
        """
        规划拆解：把用户复杂理财问题拆解为执行步骤
        """
        steps = []
        text = user_input.lower()

        # 是否需要风险测评
        if any(kw in text for kw in ["风险", "测评", "等级", "承受", "保守", "稳健", "进取"]):
            steps.append("risk_assessment")
        # 是否需要市场分析
        if any(kw in text for kw in ["市场", "行情", "指数", "趋势", "环境", "现在"]):
            steps.append("market_analysis")
        # 是否需要产品/配置
        if any(kw in text for kw in ["产品", "推荐", "配置", "理财", "怎么投", "建议",
                                      "月薪", "收入", "多少钱", "方案", "组合"]):
            steps.append("product_matching")
        # 是否需要收益测算
        if any(kw in text for kw in ["收益", "复利", "定投", "利息", "赚多少", "测算"]):
            steps.append("yield_calculation")
        # 是否需要监管信息
        if any(kw in text for kw in ["监管", "合规", "规定", "保本", "资管", "适当性"]):
            steps.append("regulation_query")

        # 默认：完整流程
        if not steps:
            steps = ["customer_profile", "market_analysis", "product_matching"]

        # 所有流程都需要合规审查 + 话术生成
        if "product_matching" in steps:
            steps.append("compliance_review")
        steps.append("dialogue_generation")

        logger.info(f"规划拆解: {user_input[:50]} -> 步骤: {steps}")
        return steps

    async def execute(self, user_id: str, user_input: str) -> dict[str, Any]:
        """
        执行多智能体协同
        Returns: {
            "response": 最终回复,
            "reasoning_chain": 推理链,
            "compliance_result": 合规结果,
            "wealth_plan": 理财方案,
            "data_sources": 数据来源,
        }
        """
        logger.info(f"═══ 多智能体协同开始 | 用户={user_id} ═══")
        logger.info(f"用户输入: {user_input[:100]}")

        # 0. 记录用户消息到短期记忆
        self.memory.add_message(user_id, "user", user_input)

        # 1. 规划拆解
        steps = self.plan(user_input)

        # 收集所有推理步骤
        all_thoughts: list[AgentThought] = []

        # 2. 客户画像（第一步必须做）
        profile_summary = await self.profile_agent.build_profile(user_id, user_input)
        all_thoughts.extend(self.profile_agent.get_reasoning_chain())
        self.profile_agent.clear_thoughts()

        # 获取用户风险等级
        ltm = self.memory.get_long_term(user_id)
        try:
            risk_level = RiskLevel(ltm.risk_level)
        except ValueError:
            risk_level = RiskLevel.CONSERVATIVE

        # 3. 市场分析（如需要）
        market_analysis = ""
        if "market_analysis" in steps:
            market_analysis = await self.market_agent.analyze_market(user_id)
            all_thoughts.extend(self.market_agent.get_reasoning_chain())
            self.market_agent.clear_thoughts()

        # 4. 产品匹配 + 资产配置（大小模型协同）
        recommendation_text = ""
        recommendations: list[RecommendationItem] = []
        if "product_matching" in steps:
            recommendation_text, recommendations = await self.product_agent.match_products(
                user_id, risk_level, ltm.preferences, market_analysis
            )
            all_thoughts.extend(self.product_agent.get_reasoning_chain())
            self.product_agent.clear_thoughts()

        # 5. 收益测算（如需要，通过工具调用）
        if "yield_calculation" in steps:
            from tools.calculators import YieldCalculationTool
            yield_tool = YieldCalculationTool()
            # 根据输入判断模式
            if "定投" in user_input or "每月" in user_input:
                yield_result = await yield_tool.execute(
                    mode="sip", monthly_invest=1000, annual_rate=0.045, years=3
                )
            else:
                yield_result = await yield_tool.execute(
                    mode="compound", principal=10000, annual_rate=0.045, years=3
                )
            recommendation_text += f"\n\n【收益测算】\n{yield_result}"

        # 6. 监管查询（如需要）
        if "regulation_query" in steps:
            from tools.regulation_kb import RegulationKnowledgeBaseTool
            reg_tool = RegulationKnowledgeBaseTool()
            reg_result = await reg_tool.execute(query=user_input[:50])
            recommendation_text += f"\n\n【监管参考】\n{reg_result}"

        # 7. 话术生成
        final_response = await self.dialogue_agent.generate_response(
            user_id=user_id,
            user_input=user_input,
            profile_summary=profile_summary,
            market_analysis=market_analysis,
            product_recommendation=recommendation_text,
            recommendations=recommendations,
        )
        all_thoughts.extend(self.dialogue_agent.get_reasoning_chain())
        self.dialogue_agent.clear_thoughts()

        # 8. 合规审查（硬隔离 - 所有输出必须经过）
        data_sources = []
        if self.retriever:
            # 收集数据来源
            for rec in recommendations:
                if rec.data_source and rec.data_source not in data_sources:
                    data_sources.append(rec.data_source)

        sanitized_response, compliance_result = await self.compliance_agent.review(
            user_id=user_id,
            content=final_response,
            risk_level=risk_level,
            recommendations=recommendations,
            data_sources=data_sources,
        )
        all_thoughts.extend(self.compliance_agent.get_reasoning_chain())
        self.compliance_agent.clear_thoughts()

        # 9. 记录助手回复到短期记忆
        self.memory.add_message(user_id, "assistant", sanitized_response)

        # 10. 构建理财方案
        wealth_plan = WealthPlan(
            user_id=user_id,
            risk_level=risk_level,
            market_analysis=market_analysis,
            recommendations=recommendations,
            risk_disclosure=settings.compliance.risk_disclosure_text,
            reasoning_chain=all_thoughts,
        )

        logger.info(f"═══ 多智能体协同完成 | 合规={'通过' if compliance_result.passed else '拦截'} ═══")

        return {
            "response": sanitized_response,
            "reasoning_chain": all_thoughts,
            "compliance_result": compliance_result,
            "wealth_plan": wealth_plan,
            "data_sources": data_sources,
            "steps_executed": steps,
            "user_risk_level": risk_level.value,
        }

    async def chat(self, user_id: str, user_input: str) -> str:
        """简化接口：直接返回对话回复"""
        result = await self.execute(user_id, user_input)
        return result["response"]

    def get_agent_status(self) -> dict:
        """获取各Agent状态"""
        return {
            "agents": list(self.agents.keys()),
            "memory_users": len(self.memory._short_term),
            "rag_documents": self.retriever.vector_store.count() if self.retriever else 0,
        }
