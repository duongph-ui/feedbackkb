-- rollback 0001: drop core tables + helper functions (reverse dependency order).
DROP TABLE IF EXISTS fbk.knowledge_doc;
DROP TABLE IF EXISTS fbk.knowledge_ref;
DROP TABLE IF EXISTS fbk.agent_task;
DROP TABLE IF EXISTS fbk.feedback_event;
DROP FUNCTION IF EXISTS fbk.event_append_only();
DROP TABLE IF EXISTS fbk.feedback_attachment;
DROP TABLE IF EXISTS fbk.feedback;
DROP FUNCTION IF EXISTS fbk.feedback_tsv_trg();
DROP TABLE IF EXISTS fbk.system_registry;
DROP TABLE IF EXISTS fbk.org;
