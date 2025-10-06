"""Embedding utilities using OpenAI APIs."""
from __future__ import annotations

from typing import Iterable, List

from openai import OpenAI

from .settings import settings

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        if not settings.has_embedding_credentials:
            raise RuntimeError("OPENAI_API_KEY is required for embeddings")
        _client = OpenAI(api_key=settings.openai_api_key)
    return _client


def embed_texts(texts: Iterable[str]) -> List[List[float]]:
    texts = list(texts)
    if not texts:
        return []
    client = _get_client()
    response = client.embeddings.create(
        model=settings.openai_embed_model,
        input=texts,
    )
    ordered = sorted(response.data, key=lambda d: d.index)
    return [item.embedding for item in ordered]


__all__ = ["embed_texts"]
