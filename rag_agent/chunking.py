"""Text chunking utilities."""
from __future__ import annotations

import itertools
import re
from dataclasses import dataclass
from typing import Iterable, Iterator, List

from .settings import settings

_sentence_splitter = re.compile(r"(?<=[.!?])\s+")


def split_sentences(text: str) -> List[str]:
    text = text.replace("\r", " ")
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [part.strip() for part in parts if part.strip()]


def _chunk_tokens(sentences: Iterable[str], max_tokens: int, overlap: int) -> Iterator[str]:
    window: List[str] = []
    token_counts: List[int] = []

    for sentence in sentences:
        tokens = sentence.split()
        token_counts.append(len(tokens))
        window.append(sentence)

        while sum(token_counts) > max_tokens and window:
            window.pop(0)
            token_counts.pop(0)

        if sum(token_counts) >= max_tokens - overlap:
            yield " ".join(window)
            # apply overlap by keeping last overlap tokens
            overlap_tokens = overlap
            trimmed_window: List[str] = []
            trimmed_counts: List[int] = []
            for s, c in zip(reversed(window), reversed(token_counts)):
                if overlap_tokens <= 0:
                    break
                trimmed_window.insert(0, s)
                trimmed_counts.insert(0, c)
                overlap_tokens -= c
            window = trimmed_window
            token_counts = trimmed_counts

    if window:
        yield " ".join(window)


@dataclass
class Chunk:
    doc_id: str
    chunk_id: int
    content: str


def chunk_text(doc_id: str, text: str) -> List[Chunk]:
    """
    Split text into chunks based on token limits with overlap.

    Args:
        doc_id: Document identifier
        text: Text to chunk

    Returns:
        List of chunks

    Raises:
        ValueError: If text is empty or only whitespace
    """
    # Validate input
    if not text or not text.strip():
        raise ValueError(f"Cannot chunk empty or whitespace-only text for doc_id: {doc_id}")

    sentences = split_sentences(text)
    chunks = []
    for idx, content in enumerate(
        _chunk_tokens(sentences, settings.max_tokens, settings.overlap_tokens)
    ):
        chunks.append(Chunk(doc_id=doc_id, chunk_id=idx, content=content))

    # Fallback for very short texts that don't produce chunks
    if not chunks and text.strip():
        chunks.append(Chunk(doc_id=doc_id, chunk_id=0, content=text.strip()))

    return chunks
