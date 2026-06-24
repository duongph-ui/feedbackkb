"""Feedback routes (Step 11/12/13).

POST   /api/feedback          submit (scope=submit, rate-limited, captcha for anon)
GET    /api/feedback          list (role=viewer+, tenant-scoped)
GET    /api/feedback/{id}     detail + events + agent_tasks
PATCH  /api/feedback/{id}     status/severity transition (role=triager+)
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from .. import db
from ..adapters import Identity
from ..config import get_settings
from ..middleware import rate_limit
from ..security.deps import require_role, require_scope
from ..service import captcha
from ..service import feedback_service as svc

router = APIRouter(prefix="/api/feedback", tags=["feedback"])


class CreateBody(BaseModel):
    system: str
    message: str
    attachment_ids: list[str] | None = None
    page_url: str | None = None
    context: dict | None = None
    captcha_token: str | None = None
    # forward/sync integration (Step 36, §3.5.4) — idempotent via external_id
    source: str | None = None
    external_system: str | None = None
    external_id: str | None = None


class PatchBody(BaseModel):
    status: str | None = None
    severity: str | None = None
    comment: str | None = None


def _enforce_tenant(ident: Identity, system: str) -> None:
    if ident.system is not None and ident.system != system:
        raise HTTPException(403, "cross-tenant access denied")


@router.post("", dependencies=[Depends(rate_limit)])
def create(body: CreateBody, request: Request,
           ident: Identity = Depends(require_scope("submit"))):
    s = get_settings()
    _enforce_tenant(ident, body.system)
    # anonymous submit must pass captcha when enabled
    if ident.user == "anonymous" and not captcha.verify(
        body.captcha_token, s.captcha, secret=""
    ):
        raise HTTPException(403, "captcha failed")
    try:
        with db.connect() as conn:
            if s.open_register:
                # trust-on-first-use: auto-create unknown system (internal nets only)
                from ..repo import system as sysrepo
                sysrepo.seed_system(conn, body.system, body.system)
            res = svc.create(
                conn, system=body.system, message=body.message,
                attachment_ids=body.attachment_ids, page_url=body.page_url,
                context=body.context, user_email=(None if ident.user == "anonymous" else ident.user),
                source=body.source or "widget",
                external_system=body.external_system, external_id=body.external_id,
                request_id=getattr(request.state, "request_id", None),
                source_ip=request.client.host if request.client else None,
            )
    except svc.FeedbackError as e:
        raise HTTPException(e.status, e.detail) from None
    return {"id": res.id, "status": res.status}


@router.get("")
def list_feedback(system: str | None = None, status: str | None = None, limit: int = 50,
                  ident: Identity = Depends(require_role("viewer"))):
    with db.connect() as conn:
        return svc.query(conn, requester_system=ident.system, system=system,
                         status=status, limit=limit)


@router.get("/{feedback_id}")
def detail(feedback_id: str, ident: Identity = Depends(require_role("viewer"))):
    try:
        with db.connect() as conn:
            return svc.get(conn, feedback_id, ident.system)
    except svc.FeedbackError as e:
        raise HTTPException(e.status, e.detail) from None


@router.patch("/{feedback_id}")
def patch(feedback_id: str, body: PatchBody, request: Request,
          ident: Identity = Depends(require_role("triager"))):
    if body.status is None and body.severity is None:
        raise HTTPException(422, "nothing to update")
    try:
        with db.connect() as conn:
            if body.status is not None:
                svc.transition(conn, feedback_id, body.status, actor_id=ident.user,
                               severity=body.severity, comment=body.comment,
                               request_id=getattr(request.state, "request_id", None))
            elif body.severity is not None:
                with conn.cursor() as cur:
                    cur.execute("UPDATE fbk.feedback SET severity=%s WHERE id=%s",
                                (body.severity, feedback_id))
                conn.commit()
    except svc.FeedbackError as e:
        raise HTTPException(e.status, e.detail) from None
    return {"ok": True}
