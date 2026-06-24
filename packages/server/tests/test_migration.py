"""Step 4 — migration 0001 invariants.

Static tests parse the SQL and prove the DDL shape WITHOUT a live DB (so they run
in CI/dev with no Postgres). Live tests (DATABASE_URL set) prove the constraints
actually reject bad data.
"""

import os

import pytest

from feedbackkb_server import db, schema

needs_db = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="DATABASE_URL not set (no live Postgres)",
)


@pytest.fixture(scope="module")
def ddl() -> str:
    return (db.migrations_dir() / "0001_fbk_core.sql").read_text(encoding="utf-8")


# --- static (no DB) ---

def test_all_eight_tables_created(ddl):
    for t in schema.TABLES:
        assert f"CREATE TABLE fbk.{t} " in ddl, f"missing table {t}"


def test_check_enums_present(ddl):
    assert "type IN ('bug','idea','question')" in ddl
    assert "source IN ('widget','api','mcp','forward','sync')" in ddl
    assert "status IN ('uploading','ready','scanned','quarantined')" in ddl
    assert "stage IN ('triage','analyze','fix','knowledge')" in ddl
    assert "status IN ('draft','trusted')" in ddl
    assert "actor_type IN ('agent','human','system')" in ddl


def test_partial_unique_for_forward_idempotency(ddl):
    assert "feedback_external_uq" in ddl
    assert "WHERE external_id IS NOT NULL" in ddl


def test_append_only_event_trigger(ddl):
    assert "event_append_only" in ddl
    assert "BEFORE UPDATE OR DELETE ON fbk.feedback_event" in ddl


def test_idempotency_key_unique(ddl):
    assert "idempotency_key   text UNIQUE" in ddl


def test_gin_tsv_index(ddl):
    assert "USING gin (search_tsv)" in ddl


# --- live (DB) ---

@needs_db
def test_apply_creates_all_tables():
    db.apply_migrations()
    with db.connect() as conn:
        rows = db.execute(
            conn,
            "SELECT table_name FROM information_schema.tables WHERE table_schema='fbk'",
        )
    names = {r[0] for r in rows}
    assert set(schema.TABLES).issubset(names)


@needs_db
def test_check_enum_rejects_bad_value():
    db.apply_migrations()
    with db.connect() as conn:
        db.execute(conn, "INSERT INTO fbk.org(id,name) VALUES (gen_random_uuid(),'o')")
        db.execute(
            conn,
            "INSERT INTO fbk.system_registry(code,name) VALUES ('T','t') ON CONFLICT DO NOTHING",
        )
        conn.commit()
        with pytest.raises(Exception):
            db.execute(
                conn,
                "INSERT INTO fbk.feedback(system,message,type) VALUES ('T','m','xxx')",
            )


@needs_db
def test_event_append_only_blocks_update():
    db.apply_migrations()
    with db.connect() as conn:
        with pytest.raises(Exception):
            db.execute(conn, "UPDATE fbk.feedback_event SET action='x'")
