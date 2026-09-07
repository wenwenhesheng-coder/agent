"""
向量存储引擎

亮点六：支持私有化部署（ChromaDB），也支持轻量级内存检索（无需GPU）。
优先从知识库拿真实业务数据，抑制幻觉。
"""
from __future__ import annotations

import hashlib
import re
from typing import Optional

import numpy as np
from loguru import logger

from config.settings import settings


# ==================== 嵌入器 ====================

class Embedder:
    """
    文本向量化器
    优先使用 sentence-transformers (BAAI/bge-small-zh)
    无依赖时降级为 TF-IDF 风格的词袋向量（保证可运行）
    """

    def __init__(self):
        self._model = None
        self._vocab: dict[str, int] = {}
        self._use_st = False
        self._try_load_st()

    def _try_load_st(self):
        """尝试加载 sentence-transformers"""
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(
                settings.rag.embedding_model,
                device="cpu",
            )
            self._use_st = True
            logger.info("已加载 sentence-transformers 向量模型")
        except Exception as e:
            logger.warning(f"sentence-transformers不可用，降级为词袋向量: {e}")
            self._use_st = False

    def _tokenize(self, text: str) -> list[str]:
        """简易中文分词（字符级+关键词）"""
        # 去标点
        text = re.sub(r"[^\u4e00-\u9fa5a-zA-Z0-9\s]", " ", text)
        # 中文按2-4字滑窗 + 英文按词
        tokens = []
        chinese = re.findall(r"[\u4e00-\u9fa5]+", text)
        for seg in chinese:
            for n in (2, 3, 4):
                for i in range(len(seg) - n + 1):
                    tokens.append(seg[i:i + n])
        english = re.findall(r"[a-zA-Z0-9]+", text.lower())
        tokens.extend(english)
        return tokens

    def _bow_embed(self, text: str, dim: int = 512) -> np.ndarray:
        """词袋向量（带哈希降维）"""
        vec = np.zeros(dim, dtype=np.float32)
        tokens = self._tokenize(text)
        for tok in tokens:
            h = int(hashlib.md5(tok.encode()).hexdigest(), 16) % dim
            vec[h] += 1.0
        # L2归一化
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec /= norm
        return vec

    def embed(self, text: str) -> np.ndarray:
        """生成文本向量"""
        if self._use_st and self._model is not None:
            vec = self._model.encode(text, normalize_embeddings=True)
            return np.array(vec, dtype=np.float32)
        return self._bow_embed(text)

    def embed_batch(self, texts: list[str]) -> np.ndarray:
        """批量向量化"""
        if self._use_st and self._model is not None:
            vecs = self._model.encode(texts, normalize_embeddings=True, batch_size=32)
            return np.array(vecs, dtype=np.float32)
        return np.array([self._bow_embed(t) for t in texts])


# ==================== 向量库 ====================

class VectorStore:
    """
    向量存储（内存版，支持持久化）
    - add: 添加文档向量
    - search: 相似度检索
    """

    def __init__(self):
        self._embedder = Embedder()
        self._ids: list[str] = []
        self._texts: list[str] = []
        self._sources: list[str] = []
        self._metas: list[dict] = []
        self._vectors: np.ndarray | None = None

    def add_documents(
        self,
        texts: list[str],
        sources: list[str],
        metas: list[dict] | None = None,
    ) -> int:
        """添加文档到向量库"""
        metas = metas or [{} for _ in texts]
        vecs = self._embedder.embed_batch(texts)
        if self._vectors is None:
            self._vectors = vecs
        else:
            self._vectors = np.vstack([self._vectors, vecs])

        for i, (text, source, meta) in enumerate(zip(texts, sources, metas)):
            doc_id = hashlib.md5(f"{source}_{i}_{text[:30]}".encode()).hexdigest()[:12]
            self._ids.append(doc_id)
            self._texts.append(text)
            self._sources.append(source)
            self._metas.append(meta)

        logger.info(f"向量库新增 {len(texts)} 个文档片段，总计 {len(self._ids)} 个")
        return len(texts)

    def search(
        self,
        query: str,
        top_k: int = 5,
        threshold: float = 0.0,
    ) -> list[dict]:
        """
        相似度检索
        Returns: [{"content","source","score","chunk_id","meta"}]
        """
        if self._vectors is None or len(self._ids) == 0:
            return []

        q_vec = self._embedder.embed(query)
        # 余弦相似度（已归一化）
        scores = self._vectors @ q_vec
        # 取top_k
        top_indices = np.argsort(scores)[::-1][:top_k]
        results = []
        for idx in top_indices:
            score = float(scores[idx])
            if score < threshold:
                continue
            results.append({
                "content": self._texts[idx],
                "source": self._sources[idx],
                "score": round(score, 4),
                "chunk_id": self._ids[idx],
                "meta": self._metas[idx],
            })
        return results

    def count(self) -> int:
        return len(self._ids)

    def clear(self) -> None:
        self._ids.clear()
        self._texts.clear()
        self._sources.clear()
        self._metas.clear()
        self._vectors = None
