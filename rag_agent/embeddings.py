"""Embedding utilities using OpenAI APIs."""
from __future__ import annotations

import logging
from typing import Iterable, List

from openai import OpenAI, APIError, APIConnectionError, RateLimitError, APITimeoutError

from .retry import retry_with_exponential_backoff
from .settings import settings

logger = logging.getLogger(__name__)

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        if not settings.has_embedding_credentials:
            raise RuntimeError("OPENAI_API_KEY is required for embeddings")
        _client = OpenAI(api_key=settings.openai_api_key)
    return _client


@retry_with_exponential_backoff(
    max_retries=3,
    initial_delay=1.0,
    retryable_exceptions=(APIConnectionError, APITimeoutError, RateLimitError, APIError),
)
def embed_texts(texts: Iterable[str]) -> List[List[float]]:
    """
    Generate embeddings for a list of texts using OpenAI API.

    Args:
        texts: Iterable of text strings to embed

    Returns:
        List of embedding vectors

    Raises:
        RuntimeError: If OpenAI API key is not configured
        APIError: If API request fails after retries
    """
    texts = list(texts)
    if not texts:
        return []

    client = _get_client()
    logger.debug("Generating embeddings for %d texts", len(texts))

    response = client.embeddings.create(
        model=settings.openai_embed_model,
        input=texts,
    )
    ordered = sorted(response.data, key=lambda d: d.index)
    return [item.embedding for item in ordered]


__all__ = ["embed_texts"]
