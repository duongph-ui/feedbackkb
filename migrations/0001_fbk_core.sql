-- 0001 core schema fbk.* (8 entities). Type B (POSUP). Matches AP §1 ERD.
-- Enforced invariants: CHECK enums, FK 2-way, partial-unique for forward idempotency,
-- append-only feedback_event (trigger), search_tsv maintained by trigger (unaccent).

-- ---------- org (tenant) ----------
CREATE TABLE fbk.org (
    id    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name  text NOT NULL,
    plan  text
);

-- ---------- system_registry ----------
CREATE TABLE fbk.system_registry (
    code             text PRIMARY KEY,                       -- "FPS" / "FPA" / "HRMS"
    org_id           uuid REFERENCES fbk.org(id) ON DELETE CASCADE,
    name             text NOT NULL,
    app_key_hash     text,                                   -- sha256(key); NEVER raw
    app_key_prefix   text,                                   -- first 8 chars for display
    scopes           jsonb NOT NULL DEFAULT '["submit"]',
    origin_allowlist text,
    key_rotated_at   timestamptz,
    active           boolean NOT NULL DEFAULT true
);

-- ---------- feedback ----------
CREATE TABLE fbk.feedback (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    system          text NOT NULL REFERENCES fbk.system_registry(code),
    user_email      text,
    page_url        text,
    type            text CHECK (type IN ('bug','idea','question')),
    message         text NOT NULL,
    name            text,
    symptom_hash    text,
    search_tsv      tsvector,                                 -- maintained by trigger
    source          text NOT NULL DEFAULT 'widget'
                      CHECK (source IN ('widget','api','mcp','forward','sync')),
    external_system text,
    external_id     text,
    context         jsonb NOT NULL DEFAULT '{}',
    severity        text CHECK (severity IN ('low','med','high','crit')),
    status          text NOT NULL DEFAULT 'new',
    has_secret      boolean NOT NULL DEFAULT false,           -- secret-scan flag (Step 11)
    dup_of          uuid REFERENCES fbk.feedback(id),
    created_at      timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX feedback_system_status_idx ON fbk.feedback (system, status);
CREATE INDEX feedback_created_idx       ON fbk.feedback (created_at);
CREATE INDEX feedback_symptom_idx       ON fbk.feedback (symptom_hash);
CREATE INDEX feedback_tsv_idx           ON fbk.feedback USING gin (search_tsv);
-- forward/sync idempotency; widget rows (external_id NULL) not constrained
CREATE UNIQUE INDEX feedback_external_uq ON fbk.feedback (system, external_system, external_id)
    WHERE external_id IS NOT NULL;

-- search_tsv trigger (unaccent is STABLE -> can't be a generated column)
CREATE FUNCTION fbk.feedback_tsv_trg() RETURNS trigger AS $$
BEGIN
    NEW.search_tsv := to_tsvector('simple', unaccent(coalesce(NEW.message, '')));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER feedback_tsv_biu BEFORE INSERT OR UPDATE OF message ON fbk.feedback
    FOR EACH ROW EXECUTE FUNCTION fbk.feedback_tsv_trg();

-- ---------- feedback_attachment ----------
CREATE TABLE fbk.feedback_attachment (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    feedback_id uuid REFERENCES fbk.feedback(id) ON DELETE CASCADE,
    system      text NOT NULL REFERENCES fbk.system_registry(code),
    storage_key text NOT NULL,
    kind        text CHECK (kind IN ('screenshot','image')),
    mime        text,
    size_bytes  integer,
    annotated   boolean NOT NULL DEFAULT false,
    redacted    boolean NOT NULL DEFAULT false,
    status      text NOT NULL DEFAULT 'uploading'
                  CHECK (status IN ('uploading','ready','scanned','quarantined')),
    expires_at  timestamptz,
    created_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX attachment_feedback_idx ON fbk.feedback_attachment (feedback_id);
CREATE INDEX attachment_expires_idx  ON fbk.feedback_attachment (expires_at);

-- ---------- feedback_event (append-only audit) ----------
CREATE TABLE fbk.feedback_event (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    -- NO FK on purpose: this table is append-only (trigger blocks UPDATE/DELETE),
    -- so a FK ON DELETE SET NULL/CASCADE would fire a blocked write when a
    -- feedback is GDPR-deleted. Keeping feedback_id as a bare uuid lets the audit
    -- trail survive the delete (dangling id is intentional, §7.6).
    feedback_id uuid,
    actor_id    text,
    actor_type  text NOT NULL CHECK (actor_type IN ('agent','human','system')),
    action      text NOT NULL,
    request_id  text,
    source_ip   text,
    old         jsonb,
    new         jsonb,
    created_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX event_feedback_idx ON fbk.feedback_event (feedback_id);

-- append-only: block UPDATE/DELETE regardless of role (trigger beats REVOKE for owner)
CREATE FUNCTION fbk.event_append_only() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'fbk.feedback_event is append-only (% blocked)', TG_OP;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER event_no_update BEFORE UPDATE OR DELETE ON fbk.feedback_event
    FOR EACH ROW EXECUTE FUNCTION fbk.event_append_only();

-- ---------- agent_task (worker queue) ----------
CREATE TABLE fbk.agent_task (
    id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    feedback_id       uuid REFERENCES fbk.feedback(id) ON DELETE CASCADE,
    stage             text NOT NULL CHECK (stage IN ('triage','analyze','fix','knowledge')),
    status            text NOT NULL DEFAULT 'queued'
                        CHECK (status IN ('queued','running','done','need_human','failed')),
    assignee_agent    text,
    idempotency_key   text UNIQUE,
    depends_on        uuid REFERENCES fbk.agent_task(id),
    retry_count       integer NOT NULL DEFAULT 0,
    lease_until       timestamptz,
    started_at        timestamptz,
    finished_at       timestamptz,
    error             text,
    result            jsonb,
    decision_needed   boolean NOT NULL DEFAULT false,
    decision_question text,
    created_at        timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX agent_task_claim_idx ON fbk.agent_task (status, created_at);

-- ---------- knowledge_ref (index/pointer) ----------
CREATE TABLE fbk.knowledge_ref (
    id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    feedback_id  uuid REFERENCES fbk.feedback(id) ON DELETE SET NULL,  -- nullable: standalone lesson
    system       text NOT NULL,
    store_ref    text NOT NULL,                              -- wiki_path (sepo) OR knowledge_doc.id (pg)
    title        text,
    kind         text CHECK (kind IN ('lesson','remediation')),
    status       text NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','trusted')),
    occurrence   integer NOT NULL DEFAULT 1,
    symptom_hash text,
    created_at   timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX knowledge_ref_system_idx  ON fbk.knowledge_ref (system);
CREATE INDEX knowledge_ref_symptom_idx ON fbk.knowledge_ref (symptom_hash);

-- ---------- knowledge_doc (content, only when adapter=pg) ----------
CREATE TABLE fbk.knowledge_doc (
    id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    system     text NOT NULL,
    slug       text,
    content    text NOT NULL,
    version    integer NOT NULL DEFAULT 1,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX knowledge_doc_system_idx ON fbk.knowledge_doc (system, slug);
