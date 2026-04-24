from __future__ import annotations

import os
from pathlib import Path


class Config:
    APP_NAME = os.getenv("APP_NAME", "adk-mini-backend")
    BASE_DIR = Path(__file__).resolve().parents[1]

    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", str(25 * 1024 * 1024)))

    UPLOAD_DIR: Path | str = os.getenv("UPLOAD_DIR", "data/uploads")
    QDRANT_PATH: Path | str = os.getenv("QDRANT_PATH", "data/qdrant")
    QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "academic_materials")

    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
    GOOGLE_EMBEDDING_MODEL = os.getenv("GOOGLE_EMBEDDING_MODEL", "models/gemini-embedding-001")

    ADK_MODEL = os.getenv("ADK_MODEL", "gemini-1.5-flash")
    ADK_ROUTER_MODEL = os.getenv("ADK_ROUTER_MODEL", ADK_MODEL)
    ADK_GENERATION_MODEL = os.getenv("ADK_GENERATION_MODEL", "gemini-2.5-flash-lite")

    RAG_RETRIEVAL_K = int(os.getenv("RAG_RETRIEVAL_K", "8"))

    TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
    TAVILY_MAX_RESULTS = int(os.getenv("TAVILY_MAX_RESULTS", "5"))

    MIN_CHUNKS_BEFORE_ENRICHMENT = int(os.getenv("MIN_CHUNKS_BEFORE_ENRICHMENT", "8"))
    MIN_SOURCE_CHARACTERS = int(os.getenv("MIN_SOURCE_CHARACTERS", "4000"))

    @staticmethod
    def _normalize_embedding_model(model_name: str) -> str:
        cleaned = model_name.strip()
        if not cleaned:
            return "models/gemini-embedding-001"

        aliases = {
            "text-embedding-004": "models/gemini-embedding-001",
            "models/text-embedding-004": "models/gemini-embedding-001",
            "gemini-embedding-001": "models/gemini-embedding-001",
            "gemini-embedding-002": "models/gemini-embedding-002",
        }
        if cleaned in aliases:
            return aliases[cleaned]

        if cleaned.startswith("models/"):
            return cleaned

        return f"models/{cleaned}"

    @classmethod
    def refresh_from_env(cls) -> None:
        cls.APP_NAME = os.getenv("APP_NAME", "adk-mini-backend")
        cls.MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", str(25 * 1024 * 1024)))

        cls.UPLOAD_DIR = os.getenv("UPLOAD_DIR", "data/uploads")
        cls.QDRANT_PATH = os.getenv("QDRANT_PATH", "data/qdrant")
        cls.QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "academic_materials")

        cls.GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
        cls.GOOGLE_EMBEDDING_MODEL = cls._normalize_embedding_model(
            os.getenv("GOOGLE_EMBEDDING_MODEL", "models/gemini-embedding-001")
        )

        cls.ADK_MODEL = os.getenv("ADK_MODEL", "gemini-2.5-flash-lite")
        cls.ADK_ROUTER_MODEL = os.getenv("ADK_ROUTER_MODEL", cls.ADK_MODEL)
        cls.ADK_GENERATION_MODEL = os.getenv("ADK_GENERATION_MODEL", "gemini-2.5-flash-lite")

        cls.RAG_RETRIEVAL_K = int(os.getenv("RAG_RETRIEVAL_K", "8"))

        cls.TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
        cls.TAVILY_MAX_RESULTS = int(os.getenv("TAVILY_MAX_RESULTS", "5"))

        cls.MIN_CHUNKS_BEFORE_ENRICHMENT = int(os.getenv("MIN_CHUNKS_BEFORE_ENRICHMENT", "8"))
        cls.MIN_SOURCE_CHARACTERS = int(os.getenv("MIN_SOURCE_CHARACTERS", "4000"))

    @classmethod
    def _resolve_dir(cls, path_value: Path | str) -> Path:
        path = Path(path_value)
        if not path.is_absolute():
            path = cls.BASE_DIR / path
        return path

    @classmethod
    def ensure_directories(cls) -> None:
        cls.refresh_from_env()
        cls.UPLOAD_DIR = cls._resolve_dir(cls.UPLOAD_DIR)
        cls.QDRANT_PATH = cls._resolve_dir(cls.QDRANT_PATH)
        cls.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        cls.QDRANT_PATH.mkdir(parents=True, exist_ok=True)

    @classmethod
    def validate_required_settings(cls) -> None:
        if not cls.GOOGLE_API_KEY:
            raise RuntimeError(
                "GOOGLE_API_KEY is required for embeddings. Set it in your environment or .env file."
            )
        if not cls.GOOGLE_EMBEDDING_MODEL:
            raise RuntimeError(
                "GOOGLE_EMBEDDING_MODEL is required. Use models/gemini-embedding-001 or models/gemini-embedding-002."
            )
