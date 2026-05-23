"""
Embedding service dùng sentence-transformers chạy local (free).
Model all-MiniLM-L6-v2 (~90MB) tự download lần đầu chạy.

DeepSeek hiện chưa có embedding API riêng, nên dùng local model
để tránh phụ thuộc API và tiết kiệm chi phí.
"""
from __future__ import annotations
from typing import List, Optional
from sentence_transformers import SentenceTransformer
from app.config import settings

_model: Optional[SentenceTransformer] = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(settings.EMBEDDING_MODEL)
    return _model


def embed_texts(texts: List[str]) -> List[List[float]]:
    model = _get_model()
    vectors = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return vectors.tolist()


def embed_query(query: str) -> List[float]:
    return embed_texts([query])[0]
