"""File ingestion pipeline."""
from __future__ import annotations

import logging
import os
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

from .chunking import Chunk, chunk_text
from .embeddings import embed_texts
from .settings import settings
from .storage import DocumentChunk, upsert_chunks

logger = logging.getLogger(__name__)

try:  # pragma: no cover - optional dependency
    from docling.document_converter import DocumentConverter
    from docling.pipeline.standard import StandardPipeline
except Exception:  # pragma: no cover
    DocumentConverter = None  # type: ignore
    StandardPipeline = None  # type: ignore


class MarkdownConverter:
    def __init__(self) -> None:
        if DocumentConverter is None or StandardPipeline is None:
            self.converter = None
        else:
            self.converter = DocumentConverter(pipeline=StandardPipeline())

    def convert(self, path: Path) -> str:
        if self.converter is None:
            raise RuntimeError(
                "Docling ist nicht installiert. Bitte `pip install docling` im App-Container ausführen."
            )
        result = self.converter.convert(path)
        return result.document.export_to_markdown()  # type: ignore[attr-defined]


_converter = MarkdownConverter()


@dataclass
class IngestionResult:
    doc_id: str
    chunks: int


def secure_filename(original_name: str) -> str:
    """
    Generate a secure filename with validated extension.

    Args:
        original_name: Original filename from user upload

    Returns:
        Secure filename with UUID and validated extension

    Raises:
        ValueError: If file extension is not allowed
    """
    ext = Path(original_name).suffix.lower()

    # Validate extension
    if ext not in settings.allowed_file_extensions:
        raise ValueError(
            f"File extension '{ext}' is not allowed. "
            f"Allowed extensions: {', '.join(settings.allowed_file_extensions)}"
        )

    return f"{uuid.uuid4().hex}{ext}"


def allowed_file(path: Path) -> bool:
    """Check if file extension is allowed."""
    return path.suffix.lower() in settings.allowed_file_extensions


def validate_file(path: Path) -> None:
    """
    Validate uploaded file for security and resource constraints.

    Args:
        path: Path to the file to validate

    Raises:
        ValueError: If file validation fails
        FileNotFoundError: If file doesn't exist
    """
    # Check if file exists
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    # Check if it's a file (not a directory)
    if not path.is_file():
        raise ValueError(f"Path is not a file: {path}")

    # Check file size
    file_size_bytes = path.stat().st_size
    max_size_bytes = settings.max_file_size_mb * 1024 * 1024

    if file_size_bytes == 0:
        raise ValueError(f"File is empty: {path.name}")

    if file_size_bytes > max_size_bytes:
        size_mb = file_size_bytes / (1024 * 1024)
        raise ValueError(
            f"File size ({size_mb:.2f} MB) exceeds maximum allowed size "
            f"({settings.max_file_size_mb} MB): {path.name}"
        )

    # Check file extension
    if not allowed_file(path):
        raise ValueError(
            f"File type not supported: {path.suffix}. "
            f"Allowed extensions: {', '.join(settings.allowed_file_extensions)}"
        )


def convert_to_markdown(path: Path) -> str:
    logger.info("Konvertiere %s nach Markdown", path)
    return _converter.convert(path)


def _chunk_to_model(chunk: Chunk, embedding: List[float]) -> DocumentChunk:
    return DocumentChunk(
        doc_id=chunk.doc_id,
        chunk_id=chunk.chunk_id,
        content=chunk.content,
        embedding=embedding,
        meta={"source": chunk.doc_id},
    )


def ingest_file(path: Path, doc_id: str | None = None) -> IngestionResult:
    """
    Ingest a single file into the database.

    Args:
        path: Path to the file to ingest
        doc_id: Optional document ID (defaults to file stem)

    Returns:
        IngestionResult with document ID and chunk count

    Raises:
        ValueError: If file validation fails
        FileNotFoundError: If file doesn't exist
    """
    # Validate file before processing
    validate_file(path)

    doc_id = doc_id or path.stem
    markdown = convert_to_markdown(path)

    # Validate that conversion produced content
    if not markdown or not markdown.strip():
        raise ValueError(f"File conversion produced no content: {path.name}")

    chunks = chunk_text(doc_id, markdown)

    if not chunks:
        raise ValueError(f"No chunks generated from file: {path.name}")

    embeddings = embed_texts([chunk.content for chunk in chunks])
    models = [_chunk_to_model(chunk, emb) for chunk, emb in zip(chunks, embeddings)]
    upsert_chunks(models)
    logger.info("Ingest abgeschlossen: %s (%s Chunks)", doc_id, len(models))
    return IngestionResult(doc_id=doc_id, chunks=len(models))


def ingest_paths(paths: Iterable[Path]) -> List[IngestionResult]:
    results: List[IngestionResult] = []
    for path in paths:
        try:
            results.append(ingest_file(path))
        except Exception as exc:  # pragma: no cover - runtime feedback
            logger.exception("Fehler bei Ingest von %s: %s", path, exc)
    return results


def discover_files(directory: Path) -> List[Path]:
    return [
        path
        for path in sorted(directory.glob("**/*"))
        if path.is_file() and allowed_file(path)
    ]


def ingest_data_directory() -> List[IngestionResult]:
    directory = Path(settings.data_dir)
    if not directory.exists():
        logger.warning("Datenverzeichnis %s existiert nicht", directory)
        return []
    paths = discover_files(directory)
    return ingest_paths(paths)


__all__ = [
    "IngestionResult",
    "ingest_file",
    "ingest_paths",
    "ingest_data_directory",
    "discover_files",
    "secure_filename",
    "validate_file",
]
