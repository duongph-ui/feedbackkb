"""Knowledge routes (Step 22/23/27) — the REST surface the MCP tools call.

GET  /api/knowledge/search   keyword search lessons (scope=read)
POST /api/knowledge/capture  write a lesson (dedupe + trust + secret-scan) (scope=submit)
POST /api/knowledge/link     link an existing lesson to a feedback (scope=submit)

These back `search_knowledge` / `capture_lesson` / `link_knowledge` in packages/mcp.
Without them the knowledge loop (pain #1) 404s.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .. import db
from ..adapters import Identity
from ..config import get_settings
from ..repo import knowledge as krepo
from ..security.deps import require_scope
from ..service import knowledge_write as kw

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


class CaptureBody(BaseModel):
    system: str
    symptom: str
    root_cause: str
    fix: str
    prevent: str
    category: str | None = None
    files: str | None = None
    source: str | None = None  # "capture-fix" (dev->trusted) | agent (->draft)


class LinkBody(BaseModel):
    feedback_id: str
    store_ref: str
    title: str | None = None


def _enforce_tenant(ident: Identity, system: str) -> None:
    if ident.system is not None and ident.system != system:
        raise HTTPException(403, "cross-tenant access denied")


def _lesson_content(b: CaptureBody) -> str:
    return (
        f"## {b.symptom}\n"
        f"- Symptom: {b.symptom}\n"
        f"- Root cause: {b.root_cause}\n"
        f"- Fix: {b.fix}\n"
        f"- File/line: {b.files or '-'}\n"
        f"- Prevention: {b.prevent}\n"
    )


@router.get("/search")
def search(query: str, system: str | None = None, limit: int = 10,
           ident: Identity = Depends(require_scope("read"))):
    # tenant-bound identity only searches its own system
    scope_system = ident.system or system
    with db.connect() as conn:
        return krepo.search_refs(conn, system=scope_system, query=query, limit=limit)


@router.post("/capture")
def capture(body: CaptureBody, ident: Identity = Depends(require_scope("submit"))):
    _enforce_tenant(ident, body.system)
    lesson = kw.Lesson(
        system=body.system,
        title=body.symptom[:120],
        content=_lesson_content(body),
        category=body.category or "general",
        prevent=body.prevent,
        root_cause=body.root_cause,
    )
    with db.connect() as conn:
        return kw.write(
            conn, lesson,
            source=body.source or "capture-fix",
            knowledge_adapter=get_settings().knowledge,
        )


@router.post("/link")
def link(body: LinkBody, ident: Identity = Depends(require_scope("submit"))):
    with db.connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT system FROM fbk.feedback WHERE id=%s", (body.feedback_id,))
            row = cur.fetchone()
        if row is None:
            raise HTTPException(404, "feedback not found")
        system = row[0]
        _enforce_tenant(ident, system)
        ref_id = kw.link_existing(
            conn, feedback_id=body.feedback_id, system=system,
            store_ref=body.store_ref, title=body.title or "linked lesson",
        )
    return {"ref_id": ref_id, "store_ref": body.store_ref}
