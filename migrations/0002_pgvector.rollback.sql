-- rollback 0002 (Step 42). Drops the embedding columns + indexes; leaves other fbk.* intact.
DROP INDEX IF EXISTS fbk.feedback_embedding_idx;
DROP INDEX IF EXISTS fbk.knowledge_doc_embedding_idx;
ALTER TABLE fbk.feedback      DROP COLUMN IF EXISTS embedding;
ALTER TABLE fbk.knowledge_doc DROP COLUMN IF EXISTS embedding;
-- extension left in place (may be shared); drop manually if truly unused:
-- DROP EXTENSION IF EXISTS vector;
