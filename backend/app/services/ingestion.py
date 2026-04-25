from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from pathlib import Path

from flask import current_app
from langchain_core.documents import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.vector_store import build_qdrant_vector_store
from app.services.tavily_enrichment import TavilyEnrichmentService
from utils.document_parser import clean_text, load_pdf_pages

logger = logging.getLogger(__name__)


class DocumentIngestionService:
    def __init__(
        self,
        qdrant_path: Path,
        collection_name: str,
        google_api_key: str,
        embedding_model: str,
        tavily_api_key: str,
        tavily_max_results: int,
        min_chunks_before_enrichment: int,
        min_source_characters: int,
    ) -> None:
        self.min_chunks_before_enrichment = min_chunks_before_enrichment
        self.min_source_characters = min_source_characters
        self.embedding_model = embedding_model

        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

        self.embeddings = GoogleGenerativeAIEmbeddings(
            model=embedding_model,
            google_api_key=google_api_key,
        )

        self.vector_store = build_qdrant_vector_store(
            persist_path=qdrant_path,
            collection_name=collection_name,
            embeddings=self.embeddings,
        )

        self.tavily = TavilyEnrichmentService(
            api_key=tavily_api_key,
            max_results=tavily_max_results,
        )

    def ingest_pdf(self, saved_path: Path, original_filename: str, document_id: str) -> dict[str, object]:
        pages = load_pdf_pages(saved_path=saved_path)
        if not pages:
            raise ValueError("The uploaded PDF did not contain extractable text.")

        ingested_at = datetime.now(timezone.utc).isoformat()
        base_chunks = self._split_and_annotate(
            pages=pages,
            document_id=document_id,
            source_file=original_filename,
            ingested_at=ingested_at,
        )
        if not base_chunks:
            raise ValueError("No non-empty chunks were produced from the uploaded PDF.")

        total_characters = sum(len(chunk.page_content) for chunk in base_chunks)
        enrichment_chunks: list[Document] = []

        if self._should_enrich(base_chunks_count=len(base_chunks), total_characters=total_characters):
            enrichment_query = self._build_enrichment_query(base_chunks, original_filename)
            enrichment_chunks = self.tavily.fetch_documents(
                query=enrichment_query,
                document_id=document_id,
                source_file=original_filename,
            )
            enrichment_chunks = self._annotate_enrichment_chunks(enrichment_chunks, ingested_at)

        all_chunks = base_chunks + enrichment_chunks
        for idx, chunk in enumerate(all_chunks):
            chunk.metadata["chunk_index"] = idx

        # Let langchain-qdrant generate UUID point IDs for compatibility with
        # local Qdrant storage.
        self.vector_store.add_documents(all_chunks)

        return {
            "document_id": document_id,
            "source_file": original_filename,
            "pages_loaded": len(pages),
            "base_chunks": len(base_chunks),
            "enrichment_chunks": len(enrichment_chunks),
            "stored_chunks": len(all_chunks),
            "enrichment_applied": bool(enrichment_chunks),
            "embedding_model": self.embedding_model,
            "vector_store": "qdrant",
            "chunking": {"chunk_size": 1000, "chunk_overlap": 200},
        }

    def _split_and_annotate(
        self,
        pages: list[Document],
        document_id: str,
        source_file: str,
        ingested_at: str,
    ) -> list[Document]:
        split_docs = self.text_splitter.split_documents(pages)

        chunks: list[Document] = []
        for doc in split_docs:
            cleaned_text = clean_text(doc.page_content)
            if not cleaned_text:
                continue

            metadata = {
                **doc.metadata,
                "document_id": document_id,
                "source_file": source_file,
                "ingested_at": ingested_at,
                "is_enrichment": False,
                "chunk_strategy": "recursive_character",
            }
            chunks.append(Document(page_content=cleaned_text, metadata=metadata))

        return chunks

    def _annotate_enrichment_chunks(self, chunks: list[Document], ingested_at: str) -> list[Document]:
        annotated: list[Document] = []
        for chunk in chunks:
            cleaned = clean_text(chunk.page_content)
            if not cleaned:
                continue

            metadata = {
                **chunk.metadata,
                "ingested_at": ingested_at,
                "chunk_strategy": "tavily_enrichment",
            }
            annotated.append(Document(page_content=cleaned, metadata=metadata))

        return annotated

    def _should_enrich(self, base_chunks_count: int, total_characters: int) -> bool:
        if not self.tavily.enabled:
            return False
        if base_chunks_count < self.min_chunks_before_enrichment:
            return True
        return total_characters < self.min_source_characters

    def _build_enrichment_query(self, chunks: list[Document], source_file: str) -> str:
        """Build a Tavily search query that stays within the 400-char API limit."""
        topic = Path(source_file).stem.replace("_", " ")
        prefix = f"academic references and prerequisites for {topic}: "

        # Tavily hard-limits queries to 400 characters.
        max_seed_len = 400 - len(prefix) - 10  # safety margin
        if max_seed_len < 30:
            return prefix.strip()

        seed_text = " ".join(chunk.page_content for chunk in chunks[:2])
        seed_text = re.sub(r"\s+", " ", seed_text).strip()[:max_seed_len]

        if seed_text:
            return f"{prefix}{seed_text}"

        return prefix.strip()


def get_ingestion_service() -> DocumentIngestionService:
    service = current_app.extensions.get("ingestion_service")
    if service is not None:
        return service

    service = DocumentIngestionService(
        qdrant_path=current_app.config["QDRANT_PATH"],
        collection_name=current_app.config["QDRANT_COLLECTION"],
        google_api_key=current_app.config["GOOGLE_API_KEY"],
        embedding_model=current_app.config["GOOGLE_EMBEDDING_MODEL"],
        tavily_api_key=current_app.config["TAVILY_API_KEY"],
        tavily_max_results=current_app.config["TAVILY_MAX_RESULTS"],
        min_chunks_before_enrichment=current_app.config["MIN_CHUNKS_BEFORE_ENRICHMENT"],
        min_source_characters=current_app.config["MIN_SOURCE_CHARACTERS"],
    )
    current_app.extensions["ingestion_service"] = service

    return service
