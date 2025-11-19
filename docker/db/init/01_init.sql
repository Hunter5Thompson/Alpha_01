-- Enable pgvector extension for vector similarity search
CREATE EXTENSION IF NOT EXISTS vector;

-- Note: The documents table is created by SQLAlchemy (storage.py) at application startup.
-- This ensures the embedding dimension matches the configured embedding model dynamically.
-- The application will call init_db() which creates tables based on settings.embedding_dimensions.
