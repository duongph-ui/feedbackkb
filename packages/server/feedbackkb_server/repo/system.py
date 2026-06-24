"""org + system_registry repository + register/rotate (Step 5).

`register_system` returns the raw app_key ONCE; the row stores only the hash +
prefix + scopes + origin_allowlist (§7.1). Lost key -> rotate.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

import psycopg

from ..security import appkey


@dataclass
class RegisterResult:
    code: str
    app_key: str           # raw — surfaced once, never persisted
    app_key_prefix: str


def create_org(conn: psycopg.Connection, name: str, plan: str | None = None) -> str:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO fbk.org(name, plan) VALUES (%s, %s) RETURNING id",
            (name, plan),
        )
        org_id = cur.fetchone()[0]
    conn.commit()
    return str(org_id)


def register_system(
    conn: psycopg.Connection,
    code: str,
    name: str,
    org_id: str | None = None,
    scopes: list[str] | None = None,
    origin_allowlist: str | None = None,
) -> RegisterResult:
    raw = appkey.generate()
    scopes = scopes or ["submit"]
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO fbk.system_registry
                (code, org_id, name, app_key_hash, app_key_prefix, scopes,
                 origin_allowlist, key_rotated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, now())
            """,
            (
                code, org_id, name,
                appkey.hash_key(raw), appkey.display_prefix(raw),
                json.dumps(scopes), origin_allowlist,
            ),
        )
    conn.commit()
    return RegisterResult(code=code, app_key=raw, app_key_prefix=appkey.display_prefix(raw))


def rotate_key(conn: psycopg.Connection, code: str) -> RegisterResult:
    raw = appkey.generate()
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE fbk.system_registry
               SET app_key_hash=%s, app_key_prefix=%s, key_rotated_at=now()
             WHERE code=%s
            """,
            (appkey.hash_key(raw), appkey.display_prefix(raw), code),
        )
        if cur.rowcount == 0:
            raise KeyError(f"system {code!r} not found")
    conn.commit()
    return RegisterResult(code=code, app_key=raw, app_key_prefix=appkey.display_prefix(raw))


def get_system(conn: psycopg.Connection, code: str) -> dict | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT code, org_id, name, app_key_hash, app_key_prefix, scopes,
                   origin_allowlist, active
              FROM fbk.system_registry WHERE code=%s
            """,
            (code,),
        )
        row = cur.fetchone()
    if row is None:
        return None
    cols = ("code", "org_id", "name", "app_key_hash", "app_key_prefix",
            "scopes", "origin_allowlist", "active")
    return dict(zip(cols, row))
