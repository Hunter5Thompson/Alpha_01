"""Vector retrieval helpers."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence

from sqlalchemy import text

from .settings import settings
from .storage import DocumentChunk, get_session


@dataclass
class RetrievedChunk:
    doc_id: str
    chunk_id: int
    content: str
    score: float
    meta: dict


SIMILARITY_SQL = text(
    """
    SELECT doc_id, chunk_id, content, meta, 1 - (embedding <=> :embedding) AS score
    FROM documents
    ORDER BY embedding <=> :embedding
    LIMIT :limit
    """
)


def similarity_search(embedding: Sequence[float], limit: int | None = None) -> List[RetrievedChunk]:
    limit = limit or settings.knn_k
    with get_session() as session:
        rows = session.execute(
            SIMILARITY_SQL,
            {"embedding": list(embedding), "limit": limit},
        ).all()
    return [
        RetrievedChunk(
            doc_id=row.doc_id,
            chunk_id=row.chunk_id,
            content=row.content,
            score=float(row.score),
            meta=row.meta or {},
        )
        for row in rows
    ]


__all__ = ["RetrievedChunk", "similarity_search"]
