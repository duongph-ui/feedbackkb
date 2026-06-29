"""Storage adapter — private object store + short-lived signed URL.

Step 3 ships the contract + `local` impl (in-memory, HMAC-signed token URL).
`gcs`/`s3` impls land in Step 7. Objects are NEVER public; reads go through
`get_signed_url`.
"""

from __future__ import annotations

import abc
import hashlib
import hmac
import os
import tempfile
import time
import uuid
from pathlib import Path


class StorageAdapter(abc.ABC):
    @abc.abstractmethod
    def put(self, data: bytes, mime: str) -> str:
        """Store bytes, return an opaque, non-guessable storage_key."""

    @abc.abstractmethod
    def get_signed_url(self, storage_key: str, ttl: int = 300) -> str:
        """Return a URL that expires after ttl seconds."""

    @abc.abstractmethod
    def get_bytes(self, storage_key: str) -> tuple[bytes, str]:
        """Fetch raw object bytes + mime. For server-side reads (e.g. handing the
        image to an MCP/agent as vision content) where a URL the LLM can't open
        is useless. ACL is enforced by the caller (attachment_service), not here."""


class LocalStorage(StorageAdapter):
    """Disk-backed store for dev/self-host-without-cloud.

    Bytes persist to a directory (FEEDBACKKB_LOCAL_DIR, default a stable temp dir)
    so they survive process restarts and are shared across requests. The previous
    in-memory dict lost every upload immediately (get_storage made a NEW instance
    per request + nothing survived restart) → attachments were never readable.
    Reads go through a signed token URL (`/local-store`) or get_bytes (server-side).
    Not for multi-node prod — use gcs/s3 there.
    """

    def __init__(self, base_dir: str | None = None) -> None:
        d = base_dir or os.environ.get("FEEDBACKKB_LOCAL_DIR") \
            or os.path.join(tempfile.gettempdir(), "feedbackkb-attachments")
        self._dir = Path(d)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._SECRET = (os.environ.get("FEEDBACKKB_LOCAL_SECRET") or "feedbackkb-local-dev").encode()

    def _path(self, key: str) -> Path:
        # key is a hex uuid (alnum only) — guard against path traversal regardless.
        if not key.isalnum():
            raise KeyError(key)
        return self._dir / key

    def put(self, data: bytes, mime: str) -> str:
        key = uuid.uuid4().hex  # no original filename -> not guessable
        p = self._path(key)
        p.write_bytes(data)
        p.with_suffix(".mime").write_text(mime or "application/octet-stream", encoding="utf-8")
        return key

    def get_signed_url(self, storage_key: str, ttl: int = 300) -> str:
        expires = int(time.time()) + ttl
        sig = self._sign(storage_key, expires)
        return f"/local-store/{storage_key}?expires={expires}&sig={sig}"

    def get_bytes(self, storage_key: str) -> tuple[bytes, str]:
        p = self._path(storage_key)
        if not p.exists():
            raise KeyError(storage_key)
        mp = p.with_suffix(".mime")
        mime = mp.read_text(encoding="utf-8") if mp.exists() else "application/octet-stream"
        return p.read_bytes(), mime

    def delete(self, storage_key: str) -> None:
        try:
            p = self._path(storage_key)
        except KeyError:
            return
        p.unlink(missing_ok=True)
        p.with_suffix(".mime").unlink(missing_ok=True)

    def _sign(self, key: str, expires: int) -> str:
        msg = f"{key}:{expires}".encode()
        return hmac.new(self._SECRET, msg, hashlib.sha256).hexdigest()[:32]

    def verify(self, storage_key: str, expires: int, sig: str) -> bool:
        if expires < int(time.time()):
            return False
        return hmac.compare_digest(sig, self._sign(storage_key, expires))


class GcsStorage(StorageAdapter):
    """Google Cloud Storage — private objects, V4 signed URLs. (Step 7)

    SDK imported lazily so the package loads without google-cloud-storage; a real
    instantiation without the SDK/bucket fails loudly.
    """

    def __init__(self, bucket: str | None = None) -> None:
        import os

        self._bucket_name = bucket or os.environ.get("GCS_BUCKET", "")
        if not self._bucket_name:
            raise RuntimeError("GCS_BUCKET not set")
        try:
            from google.cloud import storage  # noqa: F401
        except ImportError as e:
            raise RuntimeError(
                "google-cloud-storage not installed (pip install google-cloud-storage)"
            ) from e
        from google.cloud import storage

        self._client = storage.Client()
        self._bucket = self._client.bucket(self._bucket_name)

    def put(self, data: bytes, mime: str) -> str:
        key = uuid.uuid4().hex
        blob = self._bucket.blob(key)
        blob.upload_from_string(data, content_type=mime)
        return key

    def get_signed_url(self, storage_key: str, ttl: int = 300) -> str:
        from datetime import timedelta

        return self._bucket.blob(storage_key).generate_signed_url(
            version="v4", expiration=timedelta(seconds=ttl), method="GET"
        )

    def get_bytes(self, storage_key: str) -> tuple[bytes, str]:
        blob = self._bucket.blob(storage_key)
        data = blob.download_as_bytes()
        blob.reload()
        return data, blob.content_type or "application/octet-stream"


class S3Storage(StorageAdapter):
    """AWS S3 (or S3-compatible) — reads the Clevai infra env that staging/prod
    already set:

      AWS_S3_ACCESS_ID / AWS_S3_ACCESS_KEY  credentials
      AWS_S3_BUCKET_NAME                     bucket
      AWS_S3_ENDPOINT                        endpoint URL (S3-compatible / region)
      AWS_S3_PATH_UPLOADING                  key prefix (folder) for uploads
      CDN_HOST_NAME                          if set, get_signed_url returns a CDN
                                             URL instead of a presigned S3 URL

    The DB stores the FULL object key (prefix + uuid) as storage_key, so reads
    reconstruct the path without re-reading env. boto3 imported lazily so the
    package loads without it; a real instantiation without boto3 fails loudly.
    """

    def __init__(self, bucket: str | None = None) -> None:
        import os

        self._bucket_name = bucket or os.environ.get("AWS_S3_BUCKET_NAME", "") \
            or os.environ.get("S3_BUCKET", "")
        if not self._bucket_name:
            raise RuntimeError("AWS_S3_BUCKET_NAME not set")
        try:
            import boto3
        except ImportError as e:
            raise RuntimeError("boto3 not installed (pip install boto3)") from e

        # prefix: normalise to "foo/bar/" (no leading slash, single trailing slash)
        prefix = os.environ.get("AWS_S3_PATH_UPLOADING", "").strip().strip("/")
        self._prefix = f"{prefix}/" if prefix else ""
        self._cdn = os.environ.get("CDN_HOST_NAME", "").strip().rstrip("/")

        endpoint = os.environ.get("AWS_S3_ENDPOINT", "").strip() or None
        access_id = os.environ.get("AWS_S3_ACCESS_ID", "").strip() or None
        access_key = os.environ.get("AWS_S3_ACCESS_KEY", "").strip() or None
        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=access_id,
            aws_secret_access_key=access_key,
        )

    def put(self, data: bytes, mime: str) -> str:
        key = f"{self._prefix}{uuid.uuid4().hex}"  # full object key, stored in DB
        self._client.put_object(Bucket=self._bucket_name, Key=key, Body=data, ContentType=mime)
        return key

    def get_signed_url(self, storage_key: str, ttl: int = 300) -> str:
        # CDN serves the object publicly (origin-fronted) → hand back a stable CDN
        # URL when configured; else a short-lived presigned S3 URL.
        if self._cdn:
            return f"https://{self._cdn}/{storage_key}"
        return self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket_name, "Key": storage_key},
            ExpiresIn=ttl,
        )

    def get_bytes(self, storage_key: str) -> tuple[bytes, str]:
        obj = self._client.get_object(Bucket=self._bucket_name, Key=storage_key)
        return obj["Body"].read(), obj.get("ContentType") or "application/octet-stream"
