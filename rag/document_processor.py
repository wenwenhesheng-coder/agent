"""
文档处理器 —— 知识库文档切片

构建银行专属知识库：理财产品说明书、监管文件、风险揭示书、
投资者教育材料、业务规则。
做文档切片、向量化，优先从知识库拿真实业务数据。
"""
from __future__ import annotations

import re
from pathlib import Path

from loguru import logger

from config.settings import KB_DIR, settings


class DocumentProcessor:
    """文档处理：加载、切片、清洗"""

    def __init__(self):
        self.chunk_size = settings.rag.chunk_size
        self.chunk_overlap = settings.rag.chunk_overlap

    def load_directory(self, dir_path: Path | None = None) -> list[dict]:
        """
        加载目录下所有txt文档
        Returns: [{"content","source","meta"}]
        """
        dir_path = dir_path or KB_DIR
        docs = []
        for f in sorted(dir_path.glob("*.txt")):
            content = f.read_text(encoding="utf-8")
            chunks = self.chunk(content)
            for i, chunk in enumerate(chunks):
                docs.append({
                    "content": chunk,
                    "source": f.name,
                    "meta": {"chunk_index": i, "file": f.name},
                })
            logger.info(f"加载文档: {f.name} -> {len(chunks)} 个切片")
        return docs

    def chunk(self, text: str) -> list[str]:
        """
        文档切片：按段落 + 长度切分（带overlap）
        金融文档结构性强，优先按"【】"标题分段
        """
        # 按标题段切分
        sections = re.split(r"\n(?=【)", text.strip())
        chunks = []
        for section in sections:
            section = section.strip()
            if not section:
                continue
            # 超长段落再按长度切
            if len(section) <= self.chunk_size:
                chunks.append(section)
            else:
                # 滑动窗口切分
                for i in range(0, len(section), self.chunk_size - self.chunk_overlap):
                    piece = section[i:i + self.chunk_size]
                    if len(piece) > 50:  # 过滤过短片段
                        chunks.append(piece)
        return chunks if chunks else [text.strip()]

    def build_index(self, vector_store) -> int:
        """构建知识库索引（加载文档→切片→向量化→入库）"""
        docs = self.load_directory()
        if not docs:
            logger.warning("知识库目录为空，请先添加知识库文档")
            return 0
        texts = [d["content"] for d in docs]
        sources = [d["source"] for d in docs]
        metas = [d["meta"] for d in docs]
        return vector_store.add_documents(texts, sources, metas)
