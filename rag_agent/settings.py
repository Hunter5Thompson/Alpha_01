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


def _get_int(key: str, default: int, min_value: int | None = None) -> int:
    """Get integer from environment with validation."""
    value = os.getenv(key)
    if value is None:
        return default

    try:
        int_value = int(value.strip())
    except (ValueError, AttributeError) as e:
        raise ValueError(
            f"Environment variable {key}='{value}' is not a valid integer. "
            f"Using default: {default}"
        ) from e

    if min_value is not None and int_value < min_value:
        raise ValueError(
            f"Environment variable {key}={int_value} must be >= {min_value}"
        )

    return int_value


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
    max_tokens: int = _get_int("MAX_TOKENS", 220, min_value=1)
    overlap_tokens: int = _get_int("OVERLAP_TOKENS", 40, min_value=0)
    knn_k: int = _get_int("RETRIEVAL_K", 8, min_value=1)
    rerank_top_k: int = _get_int("RERANK_TOP_K", 5, min_value=1)
    max_file_size_mb: int = _get_int("MAX_FILE_SIZE_MB", 50, min_value=1)
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


# Validate settings after instantiation
def _validate_settings() -> None:
    """Validate settings for consistency."""
    if settings.overlap_tokens >= settings.max_tokens:
        raise ValueError(
            f"OVERLAP_TOKENS ({settings.overlap_tokens}) must be less than "
            f"MAX_TOKENS ({settings.max_tokens})"
        )

    # Validate file extensions start with dot
    for ext in settings.allowed_file_extensions:
        if not ext.startswith('.'):
            raise ValueError(
                f"File extension '{ext}' in ALLOWED_EXTENSIONS must start with a dot"
            )


_validate_settings()
