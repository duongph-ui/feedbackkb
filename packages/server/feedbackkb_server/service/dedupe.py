"""Feedback dedupe — 2 tiers (Step 25, CL4).

Tier 1 exact: symptom_hash match within the same system.
Tier 2 near: FTS candidates (same system, recent) ranked by the search adapter;
above threshold -> mark dup. No pgvector at P1 (decision §5 #2).
"""

from __future__ import annotations

import psycopg

from ..adapters import SearchAdapter

NEAR_THRESHOLD = 0.6


def find_exact(conn: psycopg.Connection, system: str, symptom_hash: str,
               exclude_id: str | None = None) -> str | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id FROM fbk.feedback
             WHERE system=%s AND symptom_hash=%s AND status <> 'dup'
               AND (%s::uuid IS NULL OR id <> %s::uuid)
             ORDER BY created_at LIMIT 1
            """,
            (system, symptom_hash, exclude_id, exclude_id),
        )
        row = cur.fetchone()
    return str(row[0]) if row else None


def near_candidates(conn: psycopg.Connection, system: str, message: str,
                    exclude_id: str, days: int = 30) -> list[dict]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, message FROM fbk.feedback
             WHERE system=%s AND id <> %s::uuid AND status <> 'dup'
               AND created_at > now() - (%s || ' days')::interval
               AND search_tsv @@ plainto_tsquery('simple', unaccent(%s))
             LIMIT 50
            """,
            (system, exclude_id, str(days), message),
        )
        return [{"id": str(r[0]), "system": system, "text": r[1]} for r in cur.fetchall()]


def best_near_match(search: SearchAdapter, message: str, candidates: list[dict]) -> str | None:
    ranked = search.search(message, candidates)
    if ranked and ranked[0].get("score", 0) >= NEAR_THRESHOLD:
        return ranked[0]["id"]
    return None


def mark_dup(conn: psycopg.Connection, feedback_id: str, dup_of: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE fbk.feedback SET status='dup', dup_of=%s WHERE id=%s",
            (dup_of, feedback_id),
        )
    conn.commit()
