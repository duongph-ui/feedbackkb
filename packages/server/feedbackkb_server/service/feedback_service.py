"""Feedback service — the only writer to fbk.feedback (Step 11/12/13).

create(): validate -> secret-scan -> symptom_hash -> insert -> link attachments
(tenant-checked) -> audit -> enqueue triage task.
query()/get(): tenant-scoped reads.
transition(): status-machine guard + CL2 ensure-lesson + audit.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass

import psycopg

from . import audit, secret_scan, status_machine


class FeedbackError(Exception):
    def __init__(self, status: int, detail: str):
        self.status = status
        self.detail = detail
        super().__init__(detail)


def normalize(message: str) -> str:
    return re.sub(r"\s+", " ", message.strip().lower())


def symptom_hash(message: str) -> str:
    return hashlib.sha256(normalize(message).encode()).hexdigest()


@dataclass
class CreateResult:
    id: str
    status: str
    has_secret: bool


def create(
    conn: psycopg.Connection,
    *,
    system: str,
    message: str,
    attachment_ids: list[str] | None = None,
    page_url: str | None = None,
    context: dict | None = None,
    source: str = "widget",
    user_email: str | None = None,
    external_system: str | None = None,
    external_id: str | None = None,
    request_id: str | None = None,
    source_ip: str | None = None,
) -> CreateResult:
    if not message or not message.strip():
        raise FeedbackError(422, "message is required")

    redacted, has_secret = secret_scan.scan(message)
    ctx = context or {}
    if has_secret:
        # scan context values too (don't leak via context)
        ctx = {k: secret_scan.scan(str(v))[0] for k, v in ctx.items()}

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO fbk.feedback
                (system, user_email, page_url, message, symptom_hash, source,
                 external_system, external_id, context, has_secret, status)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'new')
            ON CONFLICT (system, external_system, external_id)
                WHERE external_id IS NOT NULL DO NOTHING
            RETURNING id
            """,
            (
                system, user_email, page_url, redacted, symptom_hash(redacted), source,
                external_system, external_id, json.dumps(ctx), has_secret,
            ),
        )
        row = cur.fetchone()
        if row is None:
            # forward/sync duplicate (same external_id) -> idempotent: return existing
            cur.execute(
                "SELECT id, status FROM fbk.feedback "
                "WHERE system=%s AND external_system=%s AND external_id=%s",
                (system, external_system, external_id),
            )
            ex = cur.fetchone()
            conn.commit()
            return CreateResult(id=str(ex[0]), status=ex[1], has_secret=has_secret)
        fid = str(row[0])

        # link attachments — must belong to same tenant
        for att_id in attachment_ids or []:
            cur.execute(
                "SELECT system FROM fbk.feedback_attachment WHERE id=%s", (att_id,)
            )
            row = cur.fetchone()
            if row is None:
                raise FeedbackError(422, f"attachment {att_id} not found")
            if row[0] != system:
                raise FeedbackError(403, "cross-tenant attachment")
            cur.execute(
                "UPDATE fbk.feedback_attachment SET feedback_id=%s WHERE id=%s",
                (fid, att_id),
            )

        # enqueue triage
        cur.execute(
            """
            INSERT INTO fbk.agent_task (feedback_id, stage, status, idempotency_key)
            VALUES (%s, 'triage', 'queued', %s)
            """,
            (fid, f"triage:{fid}"),
        )
    conn.commit()

    audit.log_event(
        conn, feedback_id=fid, actor_type="system", action="create",
        request_id=request_id, source_ip=source_ip, new={"status": "new", "source": source},
    )
    return CreateResult(id=fid, status="new", has_secret=has_secret)


def apply_triage(
    conn: psycopg.Connection,
    feedback_id: str,
    *,
    type_: str | None = None,
    name: str | None = None,
    severity: str | None = None,
    dup_of: str | None = None,
    actor_id: str = "triage",
    actor_type: str = "agent",
    request_id: str | None = None,
) -> None:
    """Triage write (Step 26): set type/name/severity/dup_of + status + audit.

    The PATCH route only moves status/severity; this is the channel the Triage
    agent (or the auto-triage runtime) uses to set the fields it derives. Marking
    a duplicate routes status to 'dup'; otherwise 'triaged'.
    """
    # Validate enums up-front so a bad value returns 422 instead of bubbling a raw
    # CHECK-constraint violation as a 500 (the auto-triage agent hits this path).
    _TYPES = {"bug", "idea", "question"}
    _SEVS = {"low", "med", "high", "crit"}
    if type_ is not None and type_ not in _TYPES:
        raise FeedbackError(422, f"invalid type '{type_}' (allowed: {', '.join(sorted(_TYPES))})")
    if severity is not None and severity not in _SEVS:
        raise FeedbackError(422, f"invalid severity '{severity}' (allowed: {', '.join(sorted(_SEVS))})")

    sets, params = [], []
    for col, val in (("type", type_), ("name", name), ("severity", severity), ("dup_of", dup_of)):
        if val is not None:
            sets.append(f"{col}=%s")
            params.append(val)
    if not sets:
        raise FeedbackError(422, "nothing to triage")
    new_status = "dup" if dup_of else "triaged"
    sets.append("status=%s")
    params.append(new_status)
    params.append(feedback_id)
    with conn.cursor() as cur:
        cur.execute(f"UPDATE fbk.feedback SET {', '.join(sets)} WHERE id=%s", params)
        if cur.rowcount == 0:
            raise FeedbackError(404, "feedback not found")
    conn.commit()
    audit.log_event(
        conn, feedback_id=feedback_id, actor_id=actor_id, actor_type=actor_type,
        action="triage", request_id=request_id,
        new={"type": type_, "name": name, "severity": severity,
             "dup_of": dup_of, "status": new_status},
    )


def set_severity(
    conn: psycopg.Connection,
    feedback_id: str,
    severity: str,
    *,
    actor_id: str = "human",
    actor_type: str = "human",
    request_id: str | None = None,
) -> None:
    """Severity-only change WITH audit (§7.6) — the PATCH route used to UPDATE
    severity straight, leaving no feedback_event behind."""
    with conn.cursor() as cur:
        cur.execute("SELECT severity FROM fbk.feedback WHERE id=%s", (feedback_id,))
        row = cur.fetchone()
        if row is None:
            raise FeedbackError(404, "feedback not found")
        old = row[0]
        cur.execute("UPDATE fbk.feedback SET severity=%s WHERE id=%s", (severity, feedback_id))
    conn.commit()
    audit.log_event(
        conn, feedback_id=feedback_id, actor_id=actor_id, actor_type=actor_type,
        action="severity_change", request_id=request_id,
        old={"severity": old}, new={"severity": severity},
    )


def query(
    conn: psycopg.Connection,
    *,
    requester_system: str | None,
    system: str | None = None,
    status: str | None = None,
    limit: int = 50,
) -> list[dict]:
    clauses, params = [], []
    # tenant scoping: a system-bound identity only sees its own rows
    if requester_system is not None:
        clauses.append("system = %s")
        params.append(requester_system)
    elif system is not None:
        clauses.append("system = %s")
        params.append(system)
    if status is not None:
        clauses.append("status = %s")
        params.append(status)
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    params.append(min(limit, 200))
    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT id, system, type, severity, message, status, created_at
              FROM fbk.feedback{where}
             ORDER BY created_at DESC LIMIT %s
            """,
            params,
        )
        rows = cur.fetchall()
    cols = ("id", "system", "type", "severity", "message", "status", "created_at")
    return [dict(zip(cols, r)) for r in rows]


def get(conn: psycopg.Connection, feedback_id: str, requester_system: str | None) -> dict:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, system, type, severity, message, status, context, has_secret, created_at
              FROM fbk.feedback WHERE id=%s
            """,
            (feedback_id,),
        )
        row = cur.fetchone()
        if row is None:
            raise FeedbackError(404, "feedback not found")
        if requester_system is not None and row[1] != requester_system:
            raise FeedbackError(403, "cross-tenant access denied")
        cols = ("id", "system", "type", "severity", "message", "status",
                "context", "has_secret", "created_at")
        fb = dict(zip(cols, row))
        cur.execute(
            "SELECT actor_type, action, created_at FROM fbk.feedback_event "
            "WHERE feedback_id=%s ORDER BY created_at",
            (feedback_id,),
        )
        fb["events"] = [dict(zip(("actor_type", "action", "created_at"), r)) for r in cur.fetchall()]
        cur.execute(
            "SELECT stage, status FROM fbk.agent_task WHERE feedback_id=%s ORDER BY created_at",
            (feedback_id,),
        )
        fb["agent_tasks"] = [dict(zip(("stage", "status"), r)) for r in cur.fetchall()]
        # attachments: surface ids so the fix/agent flow knows screenshots exist and
        # can pull each via get_attachment_image (MCP) / GET …/{id}/content.
        cur.execute(
            "SELECT id, kind, mime, status FROM fbk.feedback_attachment "
            "WHERE feedback_id=%s ORDER BY created_at",
            (feedback_id,),
        )
        fb["attachments"] = [
            {"id": str(r[0]), "kind": r[1], "mime": r[2], "status": r[3]}
            for r in cur.fetchall()
        ]
    return fb


def transition(
    conn: psycopg.Connection,
    feedback_id: str,
    new_status: str,
    *,
    actor_id: str = "human",
    actor_type: str = "human",
    severity: str | None = None,
    comment: str | None = None,
    request_id: str | None = None,
) -> None:
    with conn.cursor() as cur:
        cur.execute("SELECT status, type, severity FROM fbk.feedback WHERE id=%s", (feedback_id,))
        row = cur.fetchone()
        if row is None:
            raise FeedbackError(404, "feedback not found")
        old, ftype, fsev = row
        sev = severity or fsev
        if not status_machine.is_allowed(old, new_status):
            raise FeedbackError(409, f"illegal transition {old} -> {new_status}")
        if status_machine.requires_lesson(ftype, sev, new_status):
            cur.execute(
                "SELECT 1 FROM fbk.knowledge_ref WHERE feedback_id=%s LIMIT 1", (feedback_id,)
            )
            if cur.fetchone() is None:
                raise FeedbackError(412, "resolved bug requires a knowledge_ref (CL2)")
        cur.execute(
            "UPDATE fbk.feedback SET status=%s, severity=COALESCE(%s, severity) WHERE id=%s",
            (new_status, severity, feedback_id),
        )
    conn.commit()
    audit.log_event(
        conn, feedback_id=feedback_id, actor_id=actor_id, actor_type=actor_type,
        action="status_change", request_id=request_id,
        old={"status": old}, new={"status": new_status, "comment": comment},
    )
