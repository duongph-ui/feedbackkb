"""agent_task queue (Step 28, §1).

Atomic claim via FOR UPDATE SKIP LOCKED so two workers never grab the same task;
lease/reaper recycles dead workers; retry -> dead-letter; depends_on gates stage
order. Lease/idempotency math is pure-testable; claim/reaper are DB-bound.
"""

from __future__ import annotations

from datetime import timedelta

import psycopg

DEFAULT_LEASE_S = 300
MAX_RETRY = 3


def idempotency_key(feedback_id: str, stage: str) -> str:
    return f"{stage}:{feedback_id}"


def enqueue(conn: psycopg.Connection, feedback_id: str, stage: str,
            depends_on: str | None = None) -> str | None:
    """Insert a queued task; idempotent (returns None if key already exists)."""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO fbk.agent_task (feedback_id, stage, status, idempotency_key, depends_on)
            VALUES (%s, %s, 'queued', %s, %s)
            ON CONFLICT (idempotency_key) DO NOTHING
            RETURNING id
            """,
            (feedback_id, stage, idempotency_key(feedback_id, stage), depends_on),
        )
        row = cur.fetchone()
    conn.commit()
    return str(row[0]) if row else None


def claim(conn: psycopg.Connection, agent: str, lease_s: int = DEFAULT_LEASE_S) -> dict | None:
    """Atomically claim the oldest runnable task (deps satisfied)."""
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE fbk.agent_task SET status='running', assignee_agent=%s,
                   started_at=now(), lease_until=now() + (%s || ' seconds')::interval
             WHERE id = (
                SELECT t.id FROM fbk.agent_task t
                 WHERE t.status='queued'
                   AND (t.depends_on IS NULL OR EXISTS (
                        SELECT 1 FROM fbk.agent_task d
                         WHERE d.id=t.depends_on AND d.status='done'))
                 ORDER BY t.created_at
                 FOR UPDATE SKIP LOCKED
                 LIMIT 1)
            RETURNING id, feedback_id, stage
            """,
            (agent, str(lease_s)),
        )
        row = cur.fetchone()
    conn.commit()
    if row is None:
        return None
    return {"id": str(row[0]), "feedback_id": str(row[1]), "stage": row[2]}


def complete(conn: psycopg.Connection, task_id: str, result: dict | None = None,
             status: str = "done") -> None:
    import json
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE fbk.agent_task SET status=%s, finished_at=now(), result=%s WHERE id=%s",
            (status, json.dumps(result) if result else None, task_id),
        )
    conn.commit()


def reap_expired(conn: psycopg.Connection) -> int:
    """Return dead-leased tasks to queue (retry) or dead-letter past MAX_RETRY."""
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE fbk.agent_task
               SET status = CASE WHEN retry_count >= %s THEN 'failed' ELSE 'queued' END,
                   retry_count = retry_count + 1,
                   lease_until = NULL, assignee_agent = NULL
             WHERE status='running' AND lease_until < now()
            """,
            (MAX_RETRY,),
        )
        n = cur.rowcount
    conn.commit()
    return n


def queue_depth(conn: psycopg.Connection) -> int:
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM fbk.agent_task WHERE status='queued'")
        return cur.fetchone()[0]


def lease_deadline(now, lease_s: int = DEFAULT_LEASE_S):
    return now + timedelta(seconds=lease_s)
