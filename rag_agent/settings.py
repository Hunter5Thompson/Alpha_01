"""Application configuration management."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List


def _get_bool(key: str, default: bool) -> bool:
    value = os.getenv(key)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_list(key: str, default: List[str]) -> List[str]:
    value = os.getenv(key)
    if value is None:
        return default
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    """Centralised application settings loaded from environment variables."""

    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://rag:ragpass@db:5432/ragdb",
    )
    data_dir: str = os.getenv("DATA_DIR", "/data")
    auto_ingest: bool = _get_bool("AUTO_INGEST", True)
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    openai_embed_model: str = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-large")
    rerank_provider: str = os.getenv("RERANK_PROVIDER", "openai")
    rerank_model: str = os.getenv("RERANK_MODEL", "gpt-4o-mini")
    llm_provider: str = os.getenv("LLM_PROVIDER", "anthropic")
    llm_model: str = os.getenv("LLM_MODEL", "claude-3-7-sonnet-20250219")
    anthropic_api_key: str | None = os.getenv("ANTHROPIC_API_KEY")
    max_tokens: int = int(os.getenv("MAX_TOKENS", "220"))
    overlap_tokens: int = int(os.getenv("OVERLAP_TOKENS", "40"))
    knn_k: int = int(os.getenv("RETRIEVAL_K", "8"))
    rerank_top_k: int = int(os.getenv("RERANK_TOP_K", "5"))
    allowed_file_extensions: List[str] = _get_list(
        "ALLOWED_EXTENSIONS",
        [
            ".pdf",
            ".docx",
            ".pptx",
            ".html",
            ".htm",
            ".png",
            ".jpg",
            ".jpeg",
            ".md",
            ".txt",
        ],
    )

    @property
    def has_embedding_credentials(self) -> bool:
        return bool(self.openai_api_key)

    @property
    def has_llm_credentials(self) -> bool:
        if self.llm_provider == "anthropic":
            return bool(self.anthropic_api_key)
        return bool(self.openai_api_key)

    @property
    def needs_rerank(self) -> bool:
        return bool(self.rerank_provider)

    @property
    def embedding_dimensions(self) -> int:
        model = self.openai_embed_model.lower()
        if "large" in model:
            return 3072
        if "small" in model or "mini" in model:
            return 512
        # default dimension for text-embedding-3-base
        return 1536


settings = Settings()
