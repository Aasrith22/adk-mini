from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from langchain_qdrant import QdrantVectorStore, RetrievalMode


def build_qdrant_vector_store(
    persist_path: Path,
    collection_name: str,
    embeddings,
) -> QdrantVectorStore:
    bootstrap_id = f"bootstrap-{uuid4()}"

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

    return vector_store