-- rollback 0000: drop schema fbk (CASCADE removes anything later migrations added).
-- Extensions left in place (shared, cheap, may be used elsewhere).

DROP SCHEMA IF EXISTS fbk CASCADE;
