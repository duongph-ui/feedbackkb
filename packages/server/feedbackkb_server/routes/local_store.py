"""Local-store serving route — resolves the signed URLs that LocalStorage hands out.

Only active when storage=local. The signed URL form is
`/local-store/{key}?expires=…&sig=…`; we re-verify the HMAC + expiry, then stream
the bytes. Cloud backends (gcs/s3) return their own signed URLs and never hit this.
Without this route the local signed URLs pointed at nothing (404), so human review
of screenshots silently failed.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response

from ..adapters import get_storage
from ..adapters.storage import LocalStorage
from ..config import get_settings

router = APIRouter(prefix="/local-store", tags=["attachment"])


@router.get("/{storage_key}")
def serve(storage_key: str, expires: int, sig: str):
    storage = get_storage(get_settings().storage)
    if not isinstance(storage, LocalStorage):
        raise HTTPException(404, "local store disabled")
    if not storage.verify(storage_key, expires, sig):
        raise HTTPException(403, "invalid or expired signature")
    try:
        data, mime = storage.get_bytes(storage_key)
    except KeyError:
        raise HTTPException(404, "object not found") from None
    return Response(content=data, media_type=mime)
