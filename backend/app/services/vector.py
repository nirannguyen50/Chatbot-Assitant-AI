"""
Vector store dùng ChromaDB (persistent local).
Mỗi chatbot có collection riêng: chatbot_{id}
"""
from __future__ import annotations
from typing import List, Optional
import os
import chromadb

# Tắt telemetry của ChromaDB (gây warning vô ích)
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["CHROMA_TELEMETRY"] = "False"

from app.config import settings

_client: Optional[chromadb.PersistentClient] = None


def _get_client() -> chromadb.PersistentClient:
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)
    return _client


def _collection_name(chatbot_id: int) -> str:
    return f"chatbot_{chatbot_id}"


def get_collection(chatbot_id: int):
    client = _get_client()
    return client.get_or_create_collection(
        name=_collection_name(chatbot_id),
        metadata={"hnsw:space": "cosine"},
    )


def add_document_chunks(
    chatbot_id: int,
    document_id: int,
    chunks: List[str],
    embeddings: List[List[float]],
) -> None:
    collection = get_collection(chatbot_id)
    ids = [f"doc{document_id}_chunk{i}" for i in range(len(chunks))]
    metadatas = [{"document_id": str(document_id), "chunk_index": i} for i in range(len(chunks))]

    collection.add(
        ids=ids,
        documents=chunks,
        embeddings=embeddings,
        metadatas=metadatas,
    )


def delete_document_chunks(chatbot_id: int, document_id: int) -> None:
    collection = get_collection(chatbot_id)
    results = collection.get(where={"document_id": str(document_id)})
    if results["ids"]:
        collection.delete(ids=results["ids"])


def search_similar_chunks(
    chatbot_id: int,
    query_embedding: List[float],
    top_k: int = 5,
) -> List[str]:
    collection = get_collection(chatbot_id)
    total = collection.count()
    if total == 0:
        return []

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(top_k, total),
        include=["documents", "distances"],
    )

    if not results["documents"] or not results["documents"][0]:
        return []

    # Cosine distance < 0.7 = similarity > 0.3 (đủ liên quan)
    relevant = [
        doc
        for doc, dist in zip(results["documents"][0], results["distances"][0])
        if dist < 0.7
    ]
    return relevant


def delete_chatbot_collection(chatbot_id: int) -> None:
    client = _get_client()
    try:
        client.delete_collection(_collection_name(chatbot_id))
    except Exception:
        pass
