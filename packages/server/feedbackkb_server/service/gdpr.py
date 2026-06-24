"""GDPR export / delete / erase (§7.6, Step 13b).

Delete cascades feedback -> attachments (DB row via FK ON DELETE CASCADE + the
object-store blob, which the FK can't reach) and records an audit event. Export
is tenant-scoped. Erase wipes a user's feedback for a system.
"""

from __future__ import annotations

import psycopg

from ..adapters import StorageAdapter
from . import audit


def export(conn: psycopg.Connection, *, system: str, user_email: str | None = None) -> dict:
    with conn.cursor() as cur:
        if user_email:
            cur.execute(
                "SELECT id, message, status, created_at FROM fbk.feedback "
                "WHERE system=%s AND user_email=%s",
                (system, user_email),
            )
        else:
            cur.execute(
                "SELECT id, message, status, created_at FROM fbk.feedback WHERE system=%s",
                (system,),
            )
        rows = cur.fetchall()
    cols = ("id", "message", "status", "created_at")
    return {"system": system, "feedback": [dict(zip(cols, r)) for r in rows]}


def _delete_blobs(conn: psycopg.Connection, storage: StorageAdapter, feedback_id: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT storage_key FROM fbk.feedback_attachment WHERE feedback_id=%s",
            (feedback_id,),
        )
        keys = [r[0] for r in cur.fetchall()]
    for key in keys:
        delete = getattr(storage, "delete", None)
        if callable(delete):
            delete(key)


def delete_feedback(
    conn: psycopg.Connection, storage: StorageAdapter, feedback_id: str,
    *, actor_id: str = "human",
) -> None:
    # audit BEFORE delete (append-only row survives; FK on event is SET NULL/cascade)
    audit.log_event(conn, feedback_id=feedback_id, actor_id=actor_id,
                    actor_type="human", action="delete")
    _delete_blobs(conn, storage, feedback_id)
    with conn.cursor() as cur:
        cur.execute("DELETE FROM fbk.feedback WHERE id=%s", (feedback_id,))
    conn.commit()


def erase_user(
    conn: psycopg.Connection, storage: StorageAdapter, *, system: str, user_email: str,
) -> int:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id FROM fbk.feedback WHERE system=%s AND user_email=%s",
            (system, user_email),
        )
        ids = [str(r[0]) for r in cur.fetchall()]
    for fid in ids:
        delete_feedback(conn, storage, fid)
    return len(ids)
