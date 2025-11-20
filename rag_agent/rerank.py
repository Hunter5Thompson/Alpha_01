"""Optional LLM-based reranking of retrieved chunks."""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Iterable, List, Sequence

from openai import OpenAI, APIError, APIConnectionError, RateLimitError, APITimeoutError

from .retry import retry_with_exponential_backoff
from .settings import settings

logger = logging.getLogger(__name__)


@dataclass
class RerankCandidate:
    doc_id: str
    chunk_id: int
    content: str
    score: float
    meta: dict


PROMPT_TEMPLATE = """
Du bist ein Assistant, der Dokument-Passagen nach ihrer Relevanz für die Frage sortiert.
Antworte ausschließlich als JSON-Objekt mit dem Schlüssel `ranking`, dessen Wert eine Liste von
Objekten der Form {{"doc_id": str, "chunk_id": int, "score": float}} ist. Höhere Scores sind besser.

Frage:
{question}

Passagen:
{passages}
"""


_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        if not settings.openai_api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is required for reranking. "
                "Please set the OPENAI_API_KEY environment variable."
            )
        _client = OpenAI(api_key=settings.openai_api_key)
    return _client


@retry_with_exponential_backoff(
    max_retries=3,
    initial_delay=1.0,
    retryable_exceptions=(APIConnectionError, APITimeoutError, RateLimitError, APIError),
)
def rerank(question: str, candidates: Sequence[RerankCandidate]) -> List[RerankCandidate]:
    """
    Rerank candidates using LLM-based scoring.

    Args:
        question: The search question
        candidates: List of candidates to rerank

    Returns:
        Reranked list of candidates

    Raises:
        RuntimeError: If OpenAI API key is not configured
        APIError: If API request fails after retries
    """
    if not settings.needs_rerank or not candidates:
        return list(candidates)

    logger.debug("Reranking %d candidates", len(candidates))
    client = _get_client()
    passages = [
        {
            "doc_id": c.doc_id,
            "chunk_id": c.chunk_id,
            "content": c.content,
        }
        for c in candidates
    ]
    prompt = PROMPT_TEMPLATE.format(question=question, passages=json.dumps(passages, ensure_ascii=False))
    response = client.chat.completions.create(
        model=settings.rerank_model,
        messages=[{"role": "system", "content": "Sortiere Passagen nach Relevanz"}, {"role": "user", "content": prompt}],
        temperature=0.0,
    )
    content = response.choices[0].message.content or "{}"
    try:
        data = json.loads(content)
        ranking = data.get("ranking", [])
    except json.JSONDecodeError:
        logger.warning("Failed to parse reranking response, returning original order")
        return list(candidates)

    score_map = {
        (item.get("doc_id"), item.get("chunk_id")): float(item.get("score", 0.0))
        for item in ranking
    }

    reranked = sorted(
        candidates,
        key=lambda c: score_map.get((c.doc_id, c.chunk_id), c.score),
        reverse=True,
    )
    return reranked


__all__ = ["RerankCandidate", "rerank"]
