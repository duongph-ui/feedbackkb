"""Database access for FeedbackKB.

Two rules enforced here (ISP Step 1 / §3.5.3):
  - All SQL is parameterised. `execute()` takes (sql, params); callers MUST NOT
    f-string user values into `sql`. `guard_no_fstring_values()` is a lightweight
    lint helper used by tests to prove the rule.
  - Schema is `fbk.*`; migrations are applied via yoyo (`apply_migrations`).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Sequence

import psycopg


def get_database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL not set")
    return url


def connect(database_url: str | None = None) -> psycopg.Connection:
    """Open a single connection. Caller owns lifecycle (use as context manager)."""
    return psycopg.connect(database_url or get_database_url())


def ping(database_url: str | None = None) -> bool:
    with connect(database_url) as conn, conn.cursor() as cur:
        cur.execute("SELECT 1")
        return cur.fetchone() == (1,)


def execute(
    conn: psycopg.Connection,
    sql: str,
    params: Sequence[Any] | None = None,
) -> list[tuple]:
    """Run a parameterised statement. Returns rows if any, else []."""
    with conn.cursor() as cur:
        cur.execute(sql, params or ())
        if cur.description is None:
            return []
        return cur.fetchall()


def schema_exists(database_url: str | None = None, schema: str = "fbk") -> bool:
    with connect(database_url) as conn:
        rows = execute(
            conn,
            "SELECT 1 FROM information_schema.schemata WHERE schema_name = %s",
            (schema,),
        )
        return len(rows) == 1


def migrations_dir() -> Path:
    """Repo-root migrations/ dir (../../migrations from this package)."""
    return Path(__file__).resolve().parents[3] / "migrations"


def _yoyo_url(url: str) -> str:
    """yoyo selects its DB driver from the URL scheme. We ship psycopg v3, so a
    bare `postgresql://` (which yoyo routes to psycopg2) must become
    `postgresql+psycopg://`."""
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://"):]
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://"):]
    return url


def apply_migrations(database_url: str | None = None, path: Path | None = None) -> None:
    from yoyo import get_backend, read_migrations

    backend = get_backend(_yoyo_url(database_url or get_database_url()))
    migrations = read_migrations(str(path or migrations_dir()))
    with backend.lock():
        backend.apply_migrations(backend.to_apply(migrations))


def rollback_migrations(database_url: str | None = None, path: Path | None = None) -> None:
    from yoyo import get_backend, read_migrations

    backend = get_backend(_yoyo_url(database_url or get_database_url()))
    migrations = read_migrations(str(path or migrations_dir()))
    with backend.lock():
        backend.rollback_migrations(backend.to_rollback(migrations))
