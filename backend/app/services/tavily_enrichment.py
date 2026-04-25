from __future__ import annotations

import logging
from typing import Any

from langchain_core.documents import Document
from requests import RequestException
from tavily import TavilyClient

logger = logging.getLogger(__name__)


class TavilyEnrichmentService:
    def __init__(self, api_key: str, max_results: int = 5) -> None:
        self.max_results = max_results
        self._client = TavilyClient(api_key=api_key) if api_key else None

    @property
    def enabled(self) -> bool:
        return self._client is not None

    def fetch_documents(self, query: str, document_id: str, source_file: str) -> list[Document]:
        if not self._client or not query.strip():
            return []

        try:
            response: dict[str, Any] = self._client.search(
                query=query,
                search_depth="advanced",
                include_answer=False,
                include_raw_content=False,
                max_results=self.max_results,
            )
        except Exception:
            logger.exception("Tavily enrichment failed for query: %.200s", query)
            return []

        results = response.get("results", [])
        documents: list[Document] = []
        for idx, item in enumerate(results):
            content = (item.get("content") or "").strip()
            if not content:
                continue

            documents.append(
                Document(
                    page_content=content,
                    metadata={
                        "document_id": document_id,
                        "source_file": source_file,
                        "is_enrichment": True,
                        "enrichment_rank": idx,
                        "enrichment_source_url": item.get("url"),
                        "enrichment_title": item.get("title"),
                        "enrichment_score": item.get("score"),
                    },
                )
            )

        return documents
