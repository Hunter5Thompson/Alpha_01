CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS documents (
    id BIGSERIAL PRIMARY KEY,
    doc_id TEXT NOT NULL,
    chunk_id INT NOT NULL,
    content TEXT NOT NULL,
    embedding vector(3072),
    meta JSONB DEFAULT '{}'::jsonb,
    CONSTRAINT uq_doc_chunk UNIQUE (doc_id, chunk_id)
);

CREATE INDEX IF NOT EXISTS idx_documents_doc_id ON documents (doc_id);
CREATE INDEX IF NOT EXISTS idx_documents_embedding ON documents USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
