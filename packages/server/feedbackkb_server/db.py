"""Database access for FeedbackKB.

Two rules enforced here (ISP Step 1 / §3.5.3):
  - All SQL is parameterised. `execute()` takes (sql, params); callers MUST NOT
    f-string user values into `sql`. `guard_no_fstring_values()` is a lightweight
    lint helper used by tests to prove the rule.
  - Schema is `fbk.*`; migrations are applied via yoyo (`apply_migrations`).
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Sequence

import psycopg

# Module-level pool. FeedbackKB is the SOLE process talking to its dedicated DB
# (`feedback_kb` schema `fbk` on postgres.clevai.vn) — clients reach the data only
# through this API and never get a DB grant. On a SHARED cluster, opening a fresh
# connection per request would race FPA for the SUPERUSER-reserved slots, so every
# no-arg `connect()` borrows from a bounded pool instead. Tuned via env:
#   DB_POOL_MIN (default 1) / DB_POOL_MAX (default 5)  -> hard ceiling on slots held.
_POOL = None  # lazily-built psycopg_pool.ConnectionPool


def get_database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL not set")
    return url


def _get_pool():
    """Build (once) and return the shared connection pool.

    Every pooled connection is pinned to `search_path = fbk, public` and tagged
    `application_name = feedbackkb` so a DBA can see/limit our footprint on the
    shared cluster. search_path goes through libpq `options` (not a runtime SET)
    so a transaction rollback can never reset it mid-request.
    """
    global _POOL
    if _POOL is None:
        from psycopg_pool import ConnectionPool

        _POOL = ConnectionPool(
            conninfo=get_database_url(),
            min_size=int(os.environ.get("DB_POOL_MIN", "1")),
            max_size=int(os.environ.get("DB_POOL_MAX", "5")),
            kwargs={
                "options": "-c search_path=fbk,public",
                "application_name": "feedbackkb",
            },
            open=True,
        )
    return _POOL


def close_pool() -> None:
    """Drain the pool (call on app shutdown so slots are released cleanly)."""
    global _POOL
    if _POOL is not None:
        _POOL.close()
        _POOL = None


@contextmanager
def connect(database_url: str | None = None) -> Iterator[psycopg.Connection]:
    """Yield a DB connection as a context manager.

    No-arg (the route/service path) borrows from the bounded pool and returns the
    connection on exit. An explicit `database_url` (tests, migrations, one-off
    scripts) opens a direct, unpooled connection — same semantics as before.
    Either way the block commits on clean exit and rolls back on error.
    """
    if database_url is not None:
        with psycopg.connect(database_url) as conn:
            yield conn
        return
    with _get_pool().connection() as conn:
        yield conn


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
