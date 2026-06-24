-- 0002 pgvector store for semantic dedup + search (ISP Phase 7, Step 42, AP P5 / decision #10).
-- Off-by-default: columns are nullable; nothing writes embeddings until FEEDBACKKB_EMBED != none.
-- Dim 1536 = openai text-embedding-3-small (the default adapter). A local 384-dim model
-- needs its own migration with vector(384); HNSW requires a fixed dimension.

CREATE EXTENSION IF NOT EXISTS vector;

ALTER TABLE fbk.feedback      ADD COLUMN IF NOT EXISTS embedding vector(1536);
ALTER TABLE fbk.knowledge_doc ADD COLUMN IF NOT EXISTS embedding vector(1536);

-- HNSW cosine index (better recall than ivfflat); only used when embeddings exist.
CREATE INDEX IF NOT EXISTS feedback_embedding_idx
    ON fbk.feedback USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS knowledge_doc_embedding_idx
    ON fbk.knowledge_doc USING hnsw (embedding vector_cosine_ops);
