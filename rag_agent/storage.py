"""Database utilities for persistence and retrieval."""
from __future__ import annotations

import contextlib
import logging
from typing import Iterable, Iterator, Sequence

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, Column, Index, Integer, String, Text, UniqueConstraint, create_engine, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from .settings import settings

Base = declarative_base()


class DocumentChunk(Base):
    __tablename__ = "documents"
    __table_args__ = (
        UniqueConstraint("doc_id", "chunk_id", name="uq_doc_chunk"),
        Index("idx_documents_doc_id", "doc_id"),
        # Note: IVFFLAT index is created manually after table creation in init_db()
    )

    id = Column(Integer, primary_key=True)
    doc_id = Column(String, nullable=False, index=False)  # Index defined in __table_args__
    chunk_id = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(settings.embedding_dimensions))
    meta = Column(JSON().with_variant(JSONB, "postgresql"), nullable=False, default=dict)


logger = logging.getLogger(__name__)

# Create engine with connection pool settings for production readiness
_engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,  # Verify connections before using
    pool_size=10,  # Maximum number of connections to keep open
    max_overflow=20,  # Maximum number of connections that can be created beyond pool_size
    pool_timeout=30,  # Seconds to wait before giving up on getting a connection
    pool_recycle=3600,  # Recycle connections after 1 hour
    future=True,
    echo=False,  # Set to True for SQL debugging
)
SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False, expire_on_commit=False, future=True)


def init_db() -> None:
    """
    Initialize database schema with proper vector index.

    Raises:
        SQLAlchemyError: If database connection or table creation fails
    """
    try:
        Base.metadata.create_all(_engine)
        logger.info("Database schema initialized successfully")
    except SQLAlchemyError as e:
        logger.error("Failed to create database schema: %s", e)
        raise RuntimeError(
            "Failed to initialize database. Please check database connection and credentials."
        ) from e

    # Create IVFFLAT index for vector similarity search if it doesn't exist
    # This index type is optimized for approximate nearest neighbor search
    try:
        with _engine.connect() as conn:
            # Check if index exists
            result = conn.execute(
                text(
                    "SELECT 1 FROM pg_indexes WHERE indexname = 'idx_documents_embedding'"
                )
            )
            if not result.fetchone():
                # Create IVFFLAT index for cosine similarity
                conn.execute(
                    text(
                        "CREATE INDEX idx_documents_embedding ON documents "
                        "USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
                    )
                )
                conn.commit()
                logger.info("Created IVFFLAT index for vector similarity search")
    except SQLAlchemyError as e:
        # Index creation might fail if table is empty or already exists
        # This is not critical, so we can continue
        logger.warning("Could not create vector index (may already exist): %s", e)


@contextlib.contextmanager
def get_session() -> Iterator[Session]:
    """
    Context manager for database sessions with automatic commit/rollback.

    Yields:
        Session: Database session

    Raises:
        SQLAlchemyError: If database operation fails
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except SQLAlchemyError as e:
        session.rollback()
        logger.error("Database operation failed, rolling back: %s", e)
        raise
    finally:
        session.close()


def upsert_chunks(chunks: Iterable[DocumentChunk]) -> None:
    """
    Efficiently upsert document chunks using bulk operations.

    This uses PostgreSQL's INSERT ... ON CONFLICT DO UPDATE for optimal performance.
    """
    chunks_list = list(chunks)
    if not chunks_list:
        return

    with get_session() as session:
        # Use bulk insert with ON CONFLICT DO UPDATE for better performance
        # This is much faster than individual SELECT + INSERT/UPDATE operations
        from sqlalchemy.dialects.postgresql import insert

        for chunk in chunks_list:
            stmt = insert(DocumentChunk).values(
                doc_id=chunk.doc_id,
                chunk_id=chunk.chunk_id,
                content=chunk.content,
                embedding=chunk.embedding,
                meta=chunk.meta,
            )
            # On conflict (duplicate doc_id, chunk_id), update the existing row
            stmt = stmt.on_conflict_do_update(
                constraint='uq_doc_chunk',
                set_={
                    'content': stmt.excluded.content,
                    'embedding': stmt.excluded.embedding,
                    'meta': stmt.excluded.meta,
                }
            )
            session.execute(stmt)


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
