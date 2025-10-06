"""End-to-end question answering pipeline."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .embeddings import embed_texts
from .llm import ContextChunk, generate_answer
from .rerank import RerankCandidate, rerank
from .retrieval import RetrievedChunk, similarity_search


@dataclass
class Answer:
    text: str
    sources: List[RetrievedChunk]


def answer_question(question: str) -> Answer:
    query_embedding = embed_texts([question])[0]
    retrieved = similarity_search(query_embedding)
    if not retrieved:
        return Answer(text="Es sind keine passenden Dokumente vorhanden.", sources=[])
    candidates = [
        RerankCandidate(
            doc_id=chunk.doc_id,
            chunk_id=chunk.chunk_id,
            content=chunk.content,
            score=chunk.score,
            meta=chunk.meta,
        )
        for chunk in retrieved
    ]
    ranked = rerank(question, candidates)
    context_chunks = [
        ContextChunk(doc_id=item.doc_id, chunk_id=item.chunk_id, content=item.content)
        for item in ranked[:3]
    ]
    answer = generate_answer(question, context_chunks)
    return Answer(text=answer, sources=[
        RetrievedChunk(
            doc_id=item.doc_id,
            chunk_id=item.chunk_id,
            content=item.content,
            score=item.score,
            meta=item.meta,
        )
        for item in ranked
    ])


__all__ = ["Answer", "answer_question"]
