"""
市场分析Agent（亮点一）

实时接入行情数据、研报、资讯，
进行市场解读与趋势研判。
"""
from __future__ import annotations

from loguru import logger

from agents.base_agent import BaseAgent
from core.models import AgentThought
from tools.market_data import MarketDataTool


class MarketAnalysisAgent(BaseAgent):
    name = "market_analysis_agent"
    role = "市场分析Agent"
    description = "接入行情数据与研报，进行市场解读与趋势研判"

    def get_system_prompt(self) -> str:
        return (
            "你是银行理财顾问智能体的「市场分析Agent」。\n"
            "职责：\n"
            "1. 通过工具获取实时市场行情数据（指数、债券、黄金、基金净值）\n"
            "2. 结合宏观经济面分析市场环境\n"
            "3. 进行趋势研判，为资产配置提供市场判断依据\n"
            "4. 所有分析须标注数据来源\n\n"
            "要求：\n"
            "- 市场分析须基于真实行情数据，不编造数据\n"
            "- 不做具体点位预测（合规要求）\n"
            "- 重点关注固收、权益、另类资产的整体环境\n"
            "- 输出简洁的市场环境判断，供产品匹配Agent参考"
        )

    async def analyze_market(self, user_id: str) -> str:
        """执行市场分析"""
        # 1. 获取市场行情数据
        market_tool = MarketDataTool()
        market_data = await market_tool.execute(category="all")

        # 2. 检索相关研报/知识库
        rag_context = ""
        if self.retriever:
            result = await self.retriever.retrieve("市场行情 宏观经济 债券 权益")
            rag_context = self.retriever.get_context_for_llm(result)

        # 3. LLM综合分析
        messages = [
            {"role": "system", "content": self.get_system_prompt()},
            {"role": "user", "content": f"请基于以下市场数据分析当前市场环境：\n\n{market_data}\n\n{rag_context}"},
        ]
        analysis = await self.llm.chat(messages)

        self.thoughts.append(AgentThought(
            agent_name=self.name,
            thought="获取市场行情数据并分析市场环境",
            action="get_market_data + rag_retrieve + llm_analyze",
            observation=analysis[:200],
        ))
        logger.info("市场分析Agent完成市场研判")
        return analysis
