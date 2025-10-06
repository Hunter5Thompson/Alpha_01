"""Optional LLM-based reranking of retrieved chunks."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Iterable, List, Sequence

from openai import OpenAI

from .settings import settings


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
        if not settings.has_embedding_credentials:
            raise RuntimeError("OPENAI_API_KEY is required for reranking")
        _client = OpenAI(api_key=settings.openai_api_key)
    return _client


def rerank(question: str, candidates: Sequence[RerankCandidate]) -> List[RerankCandidate]:
    if not settings.needs_rerank or not candidates:
        return list(candidates)

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
