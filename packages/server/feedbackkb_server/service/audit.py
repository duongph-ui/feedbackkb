"""Audit helper (§7.6, Step 9).

Every mutation to fbk.* records a feedback_event row. The table is append-only
(DB trigger blocks UPDATE/DELETE), so this module only ever INSERTs. actor_type
is validated against the schema enum before the round-trip.
"""

from __future__ import annotations

import json

import psycopg

from ..schema import ACTOR_TYPES


def log_event(
    conn: psycopg.Connection,
    *,
    feedback_id: str | None,
    actor_type: str,
    action: str,
    actor_id: str | None = None,
    request_id: str | None = None,
    source_ip: str | None = None,
    old: dict | None = None,
    new: dict | None = None,
) -> str:
    if actor_type not in ACTOR_TYPES:
        raise ValueError(f"actor_type must be one of {ACTOR_TYPES}, got {actor_type!r}")
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO fbk.feedback_event
                (feedback_id, actor_id, actor_type, action, request_id, source_ip, old, new)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                feedback_id, actor_id, actor_type, action, request_id, source_ip,
                json.dumps(old) if old is not None else None,
                json.dumps(new) if new is not None else None,
            ),
        )
        event_id = str(cur.fetchone()[0])
    conn.commit()
    return event_id
