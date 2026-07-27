"""
RAG 知识库检索模块
支持简单的向量搜索（基于余弦相似度，SQLite 兼容）
"""

import json
import math
import re
from typing import Optional

from sqlalchemy import text
from backend.database import SessionLocal
from backend.models.models import KnowledgeChunk, KnowledgeDocument


def simple_vector_search(query: str, top_k: int = 5) -> list:
    """
    简单的知识库搜索
    使用关键词匹配 + TF-IDF 风格评分（SQLite 兼容，不依赖 pgvector）
    """
    db = SessionLocal()
    try:
        # 分词
        query_terms = _tokenize(query)
        if not query_terms:
            return []

        # 获取所有文档块
        chunks = db.query(KnowledgeChunk).all()
        scored = []

        for chunk in chunks:
            score = _compute_similarity(query_terms, chunk.chunk_text)
            if score > 0:
                # 附加文档信息
                doc = db.query(KnowledgeDocument).filter(
                    KnowledgeDocument.id == chunk.document_id
                ).first()
                chunk.title = doc.title if doc else ""
                chunk.doc_type = doc.doc_type if doc else "general"
                chunk.score = round(score, 4)
                scored.append(chunk)

        # 按分数排序
        scored.sort(key=lambda x: x.score, reverse=True)
        return scored[:top_k]
    finally:
        db.close()


def _tokenize(text_str: str) -> list[str]:
    """简单的分词（中文按字/词切分，英文按空格）"""
    text_str = text_str.lower()
    # 提取中文字符
    chinese_chars = re.findall(r"[\u4e00-\u9fff]+", text_str)
    # 提取英文单词
    english_words = re.findall(r"[a-z]+", text_str)

    tokens = []
    for cc in chinese_chars:
        # 简单二元分词
        for i in range(len(cc)):
            tokens.append(cc[i])
        for i in range(len(cc) - 1):
            tokens.append(cc[i : i + 2])
        tokens.append(cc)  # 整词

    tokens.extend(english_words)
    return list(set(tokens))


def _compute_similarity(query_tokens: list[str], doc_text: str) -> float:
    """计算查询和文档的相似度"""
    doc_text = doc_text.lower()
    doc_len = len(doc_text)

    if doc_len == 0:
        return 0.0

    score = 0.0
    for token in query_tokens:
        count = doc_text.count(token)
        if count > 0:
            # TF 加权
            tf = math.log(1 + count)
            # 长度加权
            length_boost = math.log(1 + len(token))
            score += tf * length_boost

    # 归一化
    return score / math.log(2 + doc_len)


def embed_text(text: str) -> list[float]:
    """
    文本向量化
    模拟嵌入：使用基于字符频率的简单向量
    真实使用时接入 BGE / DashScope Embedding
    """
    import hashlib

    # 使用 hash 生成固定维度的模拟向量
    dim = 64
    vector = [0.0] * dim

    tokens = _tokenize(text)
    for i, token in enumerate(tokens):
        h = hashlib.md5(token.encode()).hexdigest()
        for j in range(min(8, dim)):
            idx = (int(h[j:j+2], 16) + i) % dim
            vector[idx] += 1.0

    # L2 归一化
    norm = math.sqrt(sum(v*v for v in vector))
    if norm > 0:
        vector = [v / norm for v in vector]

    return vector


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """余弦相似度"""
    dot = sum(av * bv for av, bv in zip(a, b))
    na = math.sqrt(sum(av*av for av in a))
    nb = math.sqrt(sum(bv*bv for bv in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)
