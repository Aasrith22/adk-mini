"""Raw text extraction utilities for document parsing.

Extracted from the ingestion service to keep parsing logic reusable
and the service layer focused on orchestration.
"""

from __future__ import annotations

import re
from pathlib import Path

import fitz
from langchain_core.documents import Document


def clean_text(text: str) -> str:
    """Collapse whitespace and strip a text string."""
    return re.sub(r"\s+", " ", text).strip()


def load_pdf_pages(saved_path: Path) -> list[Document]:
    """Extract text from every page of a PDF and return as LangChain Documents."""
    parsed_pages: list[Document] = []

    with fitz.open(str(saved_path)) as pdf_document:
        total_pages = pdf_document.page_count
        for index in range(total_pages):
            page = pdf_document.load_page(index)
            page_text = clean_text(page.get_text("text"))
            if not page_text:
                continue

            parsed_pages.append(
                Document(
                    page_content=page_text,
                    metadata={
                        "source": str(saved_path),
                        "page": index + 1,
                        "total_pages": total_pages,
                    },
                )
            )

    return parsed_pages
