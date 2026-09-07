"""
Agentic RAG 检索器（亮点二核心）

区别于传统RAG的被动检索，实现智能体检索增强：
1. 主动检索规划：根据用户问题决定检索策略
2. 多源数据融合：知识库向量检索 + 结构化工具数据
3. 来源标注与追溯：为生成内容标注信息来源
4. 实时知识更新：知识库可动态更新
"""
from __future__ import annotations

from typing import Any

from loguru import logger

from config.settings import settings
from rag.vector_store import VectorStore
from rag.document_processor import DocumentProcessor
from core.models import RetrievedChunk, RAGRetrievalResult


# 检索策略路由（Agentic RAG主动规划）
RETRIEVAL_STRATEGY_RULES: list[dict] = [
    {
        "keywords": ["产品", "理财", "收益率", "期限", "赎回", "起购", "费率", "说明书"],
        "strategy": "product_kb",
        "description": "检索理财产品知识库 + 产品查询工具",
        "use_tools": ["query_product_kb"],
        "use_rag": True,
        "rag_filter": ["说明书", "产品"],
    },
    {
        "keywords": ["监管", "合规", "规定", "保本", "适当性", "刚性兑付", "风险揭示",
                     "资管新规", "营销宣传", "双录"],
        "strategy": "regulation_kb",
        "description": "检索监管条文库 + 业务规则",
        "use_tools": ["query_regulation_kb"],
        "use_rag": True,
        "rag_filter": ["风险揭示", "业务规则", "监管"],
    },
    {
        "keywords": ["风险", "测评", "等级", "承受能力", "保守", "稳健", "进取"],
        "strategy": "risk_assessment",
        "description": "调用风险测评工具",
        "use_tools": ["assess_risk"],
        "use_rag": True,
        "rag_filter": ["投资者教育", "风险"],
    },
    {
        "keywords": ["配置", "资产", "组合", "比例", "仓位", "多少钱"],
        "strategy": "asset_allocation",
        "description": "调用资产配置计算工具",
        "use_tools": ["calculate_asset_allocation"],
        "use_rag": True,
        "rag_filter": ["投资者教育", "资产配置"],
    },
    {
        "keywords": ["收益", "复利", "定投", "测算", "利息", "多少钱能赚"],
        "strategy": "yield_calculation",
        "description": "调用收益测算工具",
        "use_tools": ["calculate_yield"],
        "use_rag": False,
    },
    {
        "keywords": ["市场", "行情", "指数", "国债", "黄金", "基金净值", "宏观"],
        "strategy": "market_data",
        "description": "调用市场行情工具",
        "use_tools": ["get_market_data"],
        "use_rag": False,
    },
    {
        "keywords": ["VaR", "压力测试", "最大损失", "风险量化", "回撤"],
        "strategy": "risk_quant",
        "description": "调用风险量化工具",
        "use_tools": ["calculate_risk_quant"],
        "use_rag": False,
    },
]


class AgenticRetriever:
    """
    Agentic RAG 检索器
    - 规划检索策略（决定检索哪些源、调用哪些工具）
    - 执行多源检索
    - 融合结果并标注来源
    """

    def __init__(self, vector_store: VectorStore):
        self.vector_store = vector_store
        self.doc_processor = DocumentProcessor()
        # 延迟加载工具注册表（避免循环依赖）
        self._tool_registry = None

    @property
    def tool_registry(self):
        if self._tool_registry is None:
            from tools import tool_registry
            self._tool_registry = tool_registry
        return self._tool_registry

    def plan_retrieval(self, query: str) -> dict:
        """
        主动检索规划：分析用户问题，决定检索策略
        这是Agentic RAG区别于传统RAG的核心
        """
        query_lower = query.lower()
        matched_strategies = []
        for rule in RETRIEVAL_STRATEGY_RULES:
            for kw in rule["keywords"]:
                if kw in query or kw.lower() in query_lower:
                    matched_strategies.append(rule)
                    break

        if not matched_strategies:
            # 默认策略：知识库全量检索
            return {
                "strategy": "general_rag",
                "description": "通用知识库检索",
                "use_tools": [],
                "use_rag": True,
                "rag_filter": [],
            }

        # 合并匹配的策略（多源融合）
        use_tools = []
        use_rag = False
        rag_filters = []
        descriptions = []
        for s in matched_strategies:
            use_tools.extend(s["use_tools"])
            if s["use_rag"]:
                use_rag = True
                rag_filters.extend(s.get("rag_filter", []))
            descriptions.append(s["description"])

        return {
            "strategy": "+".join(s["strategy"] for s in matched_strategies),
            "description": "；".join(descriptions),
            "use_tools": list(set(use_tools)),
            "use_rag": use_rag,
            "rag_filter": list(set(rag_filters)),
        }

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
    ) -> RAGRetrievalResult:
        """
        执行检索（Agentic RAG）
        1. 规划检索策略
        2. 向量检索知识库
        3. 调用相关工具获取结构化数据
        4. 融合结果并标注来源
        """
        plan = self.plan_retrieval(query)
        logger.info(f"RAG检索规划: {plan['description']}")
        logger.info(f"  使用工具: {plan['use_tools']}, RAG: {plan['use_rag']}")

        chunks: list[RetrievedChunk] = []
        sources: list[str] = []

        # 1. 向量检索知识库
        if plan["use_rag"] and self.vector_store.count() > 0:
            results = self.vector_store.search(
                query, top_k=top_k, threshold=settings.rag.similarity_threshold
            )
            # 如果有过滤器，优先匹配来源
            rag_filter = plan.get("rag_filter", [])
            if rag_filter and results:
                filtered = [
                    r for r in results
                    if any(f in r["source"] for f in rag_filter)
                ]
                if filtered:
                    results = filtered
            for r in results:
                chunks.append(RetrievedChunk(
                    content=r["content"],
                    source=r["source"],
                    score=r["score"],
                    chunk_id=r["chunk_id"],
                ))
                if r["source"] not in sources:
                    sources.append(r["source"])

        # 2. 调用工具获取结构化数据
        tool_outputs = []
        for tool_name in plan["use_tools"]:
            tool = self.tool_registry.get(tool_name)
            if tool:
                try:
                    result = await tool.execute(query=query)
                    tool_outputs.append({
                        "tool": tool_name,
                        "output": result,
                    })
                    src = f"工具:{tool_name}"
                    if src not in sources:
                        sources.append(src)
                except Exception as e:
                    logger.error(f"工具[{tool_name}]调用失败: {e}")

        # 3. 构建融合结果
        # 如果知识库无结果但工具有输出，把工具输出也作为chunk
        if not chunks and tool_outputs:
            for to in tool_outputs:
                chunks.append(RetrievedChunk(
                    content=to["output"][:500],
                    source=f"工具:{to['tool']}",
                    score=1.0,
                ))

        return RAGRetrievalResult(
            query=query,
            chunks=chunks,
            retrieval_strategy=plan["description"],
            sources=sources,
        )

    def get_context_for_llm(self, result: RAGRetrievalResult, max_chars: int = 2000) -> str:
        """
        将检索结果格式化为LLM上下文（带来源标注）
        """
        if not result.chunks:
            return ""
        lines = [
            "【以下为知识库检索结果（请基于以下真实信息回答，不要编造）】",
            f"检索策略：{result.retrieval_strategy}",
            "",
        ]
        total = 0
        for i, chunk in enumerate(result.chunks, 1):
            text = chunk.content[:max_chars - total] if total < max_chars else ""
            if not text:
                break
            lines.append(f"[片段{i} | 来源: {chunk.source} | 相关度: {chunk.score}]")
            lines.append(text)
            lines.append("")
            total += len(text)

        lines.append(f"【信息来源】: {', '.join(result.sources)}")
        return "\n".join(lines)
