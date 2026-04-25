from __future__ import annotations

from pathlib import Path
from threading import Lock
from uuid import uuid4

from langchain_qdrant import QdrantVectorStore, RetrievalMode

_VECTOR_STORE_LOCK = Lock()
_VECTOR_STORE_CACHE: dict[tuple[str, str], QdrantVectorStore] = {}


def build_qdrant_vector_store(
    persist_path: Path,
    collection_name: str,
    embeddings,
) -> QdrantVectorStore:
    cache_key = (str(persist_path.resolve()), collection_name)

    with _VECTOR_STORE_LOCK:
        cached_vector_store = _VECTOR_STORE_CACHE.get(cache_key)
        if cached_vector_store is not None:
            return cached_vector_store

        # Qdrant local mode requires point IDs to be valid UUIDs.
        bootstrap_id = uuid4().hex

        vector_store = QdrantVectorStore.from_texts(
            texts=["bootstrap"],
            embedding=embeddings,
            metadatas=[{"_bootstrap": True}],
            ids=[bootstrap_id],
            collection_name=collection_name,
            path=str(persist_path),
            retrieval_mode=RetrievalMode.DENSE,
        )

        vector_store.delete(ids=[bootstrap_id])
        _VECTOR_STORE_CACHE[cache_key] = vector_store

        return vector_store
