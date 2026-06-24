"""Feedback dedupe — 2 tiers (Step 25, CL4).

Tier 1 exact: symptom_hash match within the same system.
Tier 2 near: FTS candidates (same system, recent) ranked by the search adapter;
above threshold -> mark dup. No pgvector at P1 (decision §5 #2).
"""

from __future__ import annotations

import psycopg

from ..adapters import SearchAdapter
from . import audit

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


def _vec_literal(embedding: list[float]) -> str:
    return "[" + ",".join(repr(float(x)) for x in embedding) + "]"


def semantic_dup(conn: psycopg.Connection, system: str, embedding: list[float] | None,
                 exclude_id: str, k: int = 10, max_distance: float = 0.15) -> str | None:
    """Phase 7 (Step 44): nearest neighbour by pgvector cosine distance. dup if the
    closest non-dup feedback in the same system is within max_distance (0.15 = cosine
    similarity >= 0.85). Returns None when embeddings are off (embedding is None)."""
    if embedding is None:
        return None
    vec = _vec_literal(embedding)
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, embedding <=> %s::vector AS dist
              FROM fbk.feedback
             WHERE system=%s AND id <> %s::uuid AND status <> 'dup' AND embedding IS NOT NULL
             ORDER BY embedding <=> %s::vector
             LIMIT %s
            """,
            (vec, system, exclude_id, vec, k),
        )
        rows = cur.fetchall()
    for fid, dist in rows:
        if dist is not None and float(dist) <= max_distance:
            return str(fid)
    return None


def store_embedding(conn: psycopg.Connection, feedback_id: str, embedding: list[float] | None) -> None:
    if embedding is None:
        return
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE fbk.feedback SET embedding=%s::vector WHERE id=%s",
            (_vec_literal(embedding), feedback_id),
        )
    conn.commit()


def mark_dup(conn: psycopg.Connection, feedback_id: str, dup_of: str,
             *, actor_id: str = "triage", actor_type: str = "agent",
             request_id: str | None = None) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE fbk.feedback SET status='dup', dup_of=%s WHERE id=%s",
            (dup_of, feedback_id),
        )
    conn.commit()
    # §7.6: a dup marking is a mutation -> it must leave an audit trail too
    audit.log_event(
        conn, feedback_id=feedback_id, actor_id=actor_id, actor_type=actor_type,
        action="mark_dup", request_id=request_id,
        new={"status": "dup", "dup_of": dup_of},
    )
