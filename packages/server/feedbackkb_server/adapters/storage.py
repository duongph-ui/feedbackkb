"""Storage adapter — private object store + short-lived signed URL.

Step 3 ships the contract + `local` impl (in-memory, HMAC-signed token URL).
`gcs`/`s3` impls land in Step 7. Objects are NEVER public; reads go through
`get_signed_url`.
"""

from __future__ import annotations

import abc
import hashlib
import hmac
import time
import uuid


class StorageAdapter(abc.ABC):
    @abc.abstractmethod
    def put(self, data: bytes, mime: str) -> str:
        """Store bytes, return an opaque, non-guessable storage_key."""

    @abc.abstractmethod
    def get_signed_url(self, storage_key: str, ttl: int = 300) -> str:
        """Return a URL that expires after ttl seconds."""


class LocalStorage(StorageAdapter):
    """In-process store for dev/self-host-without-cloud. Not for prod scale."""

    _SECRET = b"feedbackkb-local-dev"  # local-only; real signing keys via env in cloud adapters

    def __init__(self) -> None:
        self._blobs: dict[str, tuple[bytes, str]] = {}

    def put(self, data: bytes, mime: str) -> str:
        key = uuid.uuid4().hex  # no original filename -> not guessable
        self._blobs[key] = (data, mime)
        return key

    def get_signed_url(self, storage_key: str, ttl: int = 300) -> str:
        expires = int(time.time()) + ttl
        sig = self._sign(storage_key, expires)
        return f"/local-store/{storage_key}?expires={expires}&sig={sig}"

    def delete(self, storage_key: str) -> None:
        self._blobs.pop(storage_key, None)

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


class S3Storage(StorageAdapter):
    """AWS S3 (or compatible) — private objects, presigned URLs. (Step 7)"""

    def __init__(self, bucket: str | None = None) -> None:
        import os

        self._bucket_name = bucket or os.environ.get("S3_BUCKET", "")
        if not self._bucket_name:
            raise RuntimeError("S3_BUCKET not set")
        try:
            import boto3
        except ImportError as e:
            raise RuntimeError("boto3 not installed (pip install boto3)") from e

        self._client = boto3.client("s3")

    def put(self, data: bytes, mime: str) -> str:
        key = uuid.uuid4().hex
        self._client.put_object(Bucket=self._bucket_name, Key=key, Body=data, ContentType=mime)
        return key

    def get_signed_url(self, storage_key: str, ttl: int = 300) -> str:
        return self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket_name, "Key": storage_key},
            ExpiresIn=ttl,
        )
