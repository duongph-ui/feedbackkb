-- 0000 init: create schema fbk + extensions. Tables land in 0001 (Step 4).
-- yoyo applies each statement; rollback pair in 0000_init_schema.rollback.sql.

CREATE SCHEMA IF NOT EXISTS fbk;

-- unaccent: Vietnamese full-text dedupe needs accent-folding (ISP Step 4 enrich).
CREATE EXTENSION IF NOT EXISTS unaccent;

-- gen_random_uuid() for uuid PKs.
CREATE EXTENSION IF NOT EXISTS pgcrypto;
