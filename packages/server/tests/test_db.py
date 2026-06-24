"""Step 1 — db_client + migration runner.

Live-DB tests self-skip when DATABASE_URL is unset (no Postgres in CI/dev box).
The scheme-normalisation and migrations-dir tests run without a DB.
"""

import os

import pytest

from feedbackkb_server import db

needs_db = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="DATABASE_URL not set (no live Postgres)",
)


# --- no-DB unit tests ---

def test_yoyo_url_normalises_to_psycopg3():
    assert db._yoyo_url("postgresql://u:p@h:5432/d") == "postgresql+psycopg://u:p@h:5432/d"
    assert db._yoyo_url("postgres://u:p@h/d") == "postgresql+psycopg://u:p@h/d"
    # already-qualified scheme left untouched
    assert db._yoyo_url("postgresql+psycopg://x") == "postgresql+psycopg://x"


def test_migrations_dir_has_init_migration():
    mdir = db.migrations_dir()
    assert mdir.is_dir(), f"{mdir} should exist"
    assert (mdir / "0000_init_schema.sql").exists()


def test_get_database_url_raises_when_unset(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(RuntimeError):
        db.get_database_url()


# --- live-DB tests (Step 1 acceptance) ---

@needs_db
def test_connect_and_ping():
    assert db.ping() is True


@needs_db
def test_apply_migration_creates_schema_fbk():
    db.apply_migrations()
    assert db.schema_exists(schema="fbk") is True


@needs_db
def test_param_sql_executes():
    with db.connect() as conn:
        rows = db.execute(conn, "SELECT %s::int", (42,))
    assert rows == [(42,)]


@needs_db
def test_rollback_then_apply_idempotent():
    db.apply_migrations()
    db.rollback_migrations()
    assert db.schema_exists(schema="fbk") is False
    db.apply_migrations()
    assert db.schema_exists(schema="fbk") is True
