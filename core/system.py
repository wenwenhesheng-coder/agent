"""
系统初始化模块

负责初始化各层组件并构建依赖关系：
- 向量存储 + RAG检索器
- 记忆引擎
- 多智能体协调器
- 合规拦截器
"""
from __future__ import annotations

from loguru import logger

from rag.vector_store import VectorStore
from rag.document_processor import DocumentProcessor
from rag.retriever import AgenticRetriever
from memory.memory_engine import MemoryEngine
from agents.orchestrator import AgentOrchestrator
from compliance.interceptor import ComplianceInterceptor


class SystemContainer:
    """
    系统容器（单例）
    管理所有组件的生命周期和依赖注入
    """

    _instance: "SystemContainer | None" = None

    def __init__(self):
        self.vector_store: VectorStore | None = None
        self.retriever: AgenticRetriever | None = None
        self.memory_engine: MemoryEngine | None = None
        self.orchestrator: AgentOrchestrator | None = None
        self.compliance_interceptor: ComplianceInterceptor | None = None
        self._initialized = False

    @classmethod
    def get_instance(cls) -> "SystemContainer":
        if cls._instance is None:
            cls._instance = SystemContainer()
        return cls._instance

    async def initialize(self) -> None:
        """初始化所有组件"""
        if self._initialized:
            return

        logger.info("═══ 系统初始化开始 ═══")

        # 1. 向量存储 + RAG
        self.vector_store = VectorStore()
        doc_processor = DocumentProcessor()
        doc_count = doc_processor.build_index(self.vector_store)
        logger.info(f"知识库索引构建完成: {doc_count} 个文档片段")

        self.retriever = AgenticRetriever(self.vector_store)

        # 2. 记忆引擎
        self.memory_engine = MemoryEngine()

        # 3. 多智能体协调器
        self.orchestrator = AgentOrchestrator(self.memory_engine, self.retriever)

        # 4. 合规拦截器
        self.compliance_interceptor = ComplianceInterceptor()

        self._initialized = True
        logger.info("═══ 系统初始化完成 ═══")
        logger.info(f"  向量库文档数: {self.vector_store.count()}")
        logger.info(f"  Agent数: {len(self.orchestrator.agents)}")
        logger.info(f"  合规规则数: {len(self.compliance_interceptor.rule_engine.rules)}")

    def get_orchestrator(self) -> AgentOrchestrator:
        if not self.orchestrator:
            raise RuntimeError("系统未初始化，请先调用initialize()")
        return self.orchestrator

    def get_status(self) -> dict:
        """获取系统状态"""
        return {
            "initialized": self._initialized,
            "vector_store_docs": self.vector_store.count() if self.vector_store else 0,
            "agents": list(self.orchestrator.agents.keys()) if self.orchestrator else [],
            "compliance_rules": (
                len(self.compliance_interceptor.rule_engine.rules)
                if self.compliance_interceptor else 0
            ),
            "memory_users": (
                len(self.memory_engine._short_term)
                if self.memory_engine else 0
            ),
        }


# 全局单例
system = SystemContainer.get_instance()
