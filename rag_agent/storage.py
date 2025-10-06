"""Database utilities for persistence and retrieval."""
from __future__ import annotations

import contextlib
from typing import Iterable, Iterator, Sequence

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, Column, Integer, String, Text, UniqueConstraint, create_engine, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from .settings import settings

Base = declarative_base()


class DocumentChunk(Base):
    __tablename__ = "documents"
    __table_args__ = (UniqueConstraint("doc_id", "chunk_id", name="uq_doc_chunk"),)

    id = Column(Integer, primary_key=True)
    doc_id = Column(String, nullable=False)
    chunk_id = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(settings.embedding_dimensions))
    meta = Column(JSON().with_variant(JSONB, "postgresql"), nullable=False, default=dict)


_engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False, expire_on_commit=False, future=True)


def init_db() -> None:
    Base.metadata.create_all(_engine)


@contextlib.contextmanager
def get_session() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except SQLAlchemyError:
        session.rollback()
        raise
    finally:
        session.close()


def upsert_chunks(chunks: Iterable[DocumentChunk]) -> None:
    with get_session() as session:
        for chunk in chunks:
            existing = (
                session.query(DocumentChunk)
                .filter(
                    DocumentChunk.doc_id == chunk.doc_id,
                    DocumentChunk.chunk_id == chunk.chunk_id,
                )
                .one_or_none()
            )
            if existing:
                existing.content = chunk.content
                existing.embedding = chunk.embedding
                existing.meta = chunk.meta
            else:
                session.add(chunk)


def fetch_chunks(limit: int) -> Sequence[DocumentChunk]:
    with get_session() as session:
        return (
            session.query(DocumentChunk)
            .order_by(DocumentChunk.doc_id, DocumentChunk.chunk_id)
            .limit(limit)
            .all()
        )


def chunk_count() -> int:
    with get_session() as session:
        return session.query(func.count(DocumentChunk.id)).scalar() or 0


__all__ = [
    "DocumentChunk",
    "SessionLocal",
    "get_session",
    "init_db",
    "upsert_chunks",
    "fetch_chunks",
    "chunk_count",
]
