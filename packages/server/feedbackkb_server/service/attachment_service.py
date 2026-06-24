"""Attachment service (§7.3, Step 8/CL6).

Upload flow: store bytes in the private object store -> insert row (status
'uploading') -> scan -> 'ready'/'quarantined' -> set retention. Reads go through
a signed URL with an ACL check (system/org). Never returns a public URL.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import psycopg

from ..adapters import StorageAdapter
from . import scan

ALLOWED_MIME = {"image/png", "image/webp", "image/jpeg"}
MAX_SIZE = 10 * 1024 * 1024  # 10 MB


class AttachmentError(Exception):
    def __init__(self, status: int, detail: str):
        self.status = status
        self.detail = detail
        super().__init__(detail)


@dataclass
class AttachmentResult:
    attachment_id: str
    status: str


def validate(data: bytes, mime: str) -> None:
    if mime not in ALLOWED_MIME:
        raise AttachmentError(415, f"unsupported mime {mime!r}")
    if len(data) > MAX_SIZE:
        raise AttachmentError(413, "file too large")


def create_attachment(
    conn: psycopg.Connection,
    storage: StorageAdapter,
    *,
    system: str,
    data: bytes,
    mime: str,
    kind: str = "screenshot",
    scan_mode: str = "off",
    retention_days: int = 90,
    feedback_id: str | None = None,
) -> AttachmentResult:
    validate(data, mime)
    storage_key = storage.put(data, mime)
    status = scan.scan_status(data, scan_mode)
    expires = datetime.now(timezone.utc) + timedelta(days=retention_days)
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO fbk.feedback_attachment
                (feedback_id, system, storage_key, kind, mime, size_bytes,
                 status, expires_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (feedback_id, system, storage_key, kind, mime, len(data), status, expires),
        )
        att_id = str(cur.fetchone()[0])
    conn.commit()
    return AttachmentResult(attachment_id=att_id, status=status)


def get_signed_url(
    conn: psycopg.Connection,
    storage: StorageAdapter,
    attachment_id: str,
    requester_system: str | None,
    ttl: int = 300,
) -> str:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT system, storage_key, status FROM fbk.feedback_attachment WHERE id=%s",
            (attachment_id,),
        )
        row = cur.fetchone()
    if row is None:
        raise AttachmentError(404, "attachment not found")
    system, storage_key, status = row
    # ACL: cross-tenant read denied
    if requester_system is not None and requester_system != system:
        raise AttachmentError(403, "cross-tenant access denied")
    if status == "quarantined":
        raise AttachmentError(403, "attachment quarantined")
    return storage.get_signed_url(storage_key, ttl=ttl)
