"""Adapter factory — pick impl per concern from config (standalone-first §6.1).

Selecting `local` / `keyword` / `none` / `pg` gives a build with zero Clevai or
cloud dependency. Cloud + sepo impls register in later steps; unknown names
raise loudly so a typo in ENV never silently downgrades behaviour.

NOTE: ISP §6.2 draws `adapters/` as a top-level dir. For a single importable
Python package we nest it under `feedbackkb_server.adapters`; the public OSS
split can re-export from a top-level path later.
"""

from __future__ import annotations

from typing import Callable

from .auth import AppKeyAuth, AuthAdapter, AuthError, Identity, JwtAuth, NoneAuth
from .knowledge import InMemoryKnowledgeStore, KnowledgeStore, Lesson, SepoKnowledgeStore
from .search import KeywordSearch, PgVectorSearch, SearchAdapter
from .storage import GcsStorage, LocalStorage, S3Storage, StorageAdapter

_STORAGE = {"local": LocalStorage, "gcs": GcsStorage, "s3": S3Storage}
_SEARCH = {"keyword": KeywordSearch, "pgvector": PgVectorSearch}
_AUTH = {"none", "jwt", "appkey"}
_KNOWLEDGE = {"pg": InMemoryKnowledgeStore, "sepo": SepoKnowledgeStore}


def _pick(registry: dict, name: str, concern: str):
    try:
        return registry[name]()
    except KeyError:
        raise ValueError(
            f"unknown {concern} adapter {name!r}; available: {sorted(registry)}"
        ) from None


def get_storage(name: str) -> StorageAdapter:
    return _pick(_STORAGE, name, "storage")


def get_search(name: str) -> SearchAdapter:
    return _pick(_SEARCH, name, "search")


def get_auth(
    name: str,
    *,
    secret: str | None = None,
    lookup: Callable[[str], dict | None] | None = None,
) -> AuthAdapter:
    if name == "none":
        return NoneAuth()
    if name == "jwt":
        return JwtAuth(secret or "")
    if name == "appkey":
        if lookup is None:
            raise ValueError("appkey adapter requires a lookup callable")
        return AppKeyAuth(lookup)
    raise ValueError(f"unknown auth adapter {name!r}; available: {sorted(_AUTH)}")


def get_knowledge(name: str) -> KnowledgeStore:
    return _pick(_KNOWLEDGE, name, "knowledge")


__all__ = [
    "AuthAdapter", "AuthError", "Identity", "NoneAuth", "JwtAuth", "AppKeyAuth",
    "SearchAdapter", "KeywordSearch", "PgVectorSearch",
    "StorageAdapter", "LocalStorage", "GcsStorage", "S3Storage",
    "KnowledgeStore", "InMemoryKnowledgeStore", "SepoKnowledgeStore", "Lesson",
    "get_storage", "get_search", "get_auth", "get_knowledge",
]
