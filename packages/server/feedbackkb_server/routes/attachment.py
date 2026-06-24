"""Attachment routes (Step 8/CL6).

POST /api/feedback/attachment   — multipart upload, returns {attachment_id} (no url)
GET  /api/feedback/attachment/{id} — returns a short-lived signed URL (ACL checked)
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, UploadFile

from .. import db
from .. import observability as obs
from ..adapters import Identity, get_storage
from ..config import get_settings
from ..middleware import rate_limit
from ..security.deps import get_identity, require_scope
from ..service import attachment_service as svc

router = APIRouter(prefix="/api/feedback/attachment", tags=["attachment"])


def _storage():
    return get_storage(get_settings().storage)


@router.post("", dependencies=[Depends(rate_limit)])
async def upload(file: UploadFile, ident: Identity = Depends(require_scope("submit"))):
    s = get_settings()
    if ident.system is None:
        raise HTTPException(400, "system required")
    data = await file.read()
    try:
        with db.connect() as conn:
            res = svc.create_attachment(
                conn, _storage(), system=ident.system, data=data,
                mime=file.content_type or "application/octet-stream",
                scan_mode=s.scan, retention_days=s.attachment_retention_days,
            )
    except svc.AttachmentError as e:
        obs.UPLOAD_FAIL.inc()
        raise HTTPException(e.status, e.detail) from None
    return {"attachment_id": res.attachment_id, "status": res.status}


@router.get("/{attachment_id}")
def signed(attachment_id: str, ident: Identity = Depends(get_identity)):
    try:
        with db.connect() as conn:
            url = svc.get_signed_url(conn, _storage(), attachment_id, ident.system)
    except svc.AttachmentError as e:
        raise HTTPException(e.status, e.detail) from None
    return {"url": url}
