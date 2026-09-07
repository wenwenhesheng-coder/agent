"""
Agentic RAG 检索增强生成模块（亮点二）

区别于传统RAG的被动检索：
- 主动检索规划：Agent自主决定检索哪些知识库、调用哪些工具
- 多源数据融合：结构化数据(API) + 非结构化文本(研报/说明书)
- 来源标注与追溯：为生成内容标注信息来源
"""
from rag.vector_store import VectorStore
from rag.document_processor import DocumentProcessor
from rag.retriever import AgenticRetriever

__all__ = ["VectorStore", "DocumentProcessor", "AgenticRetriever"]
