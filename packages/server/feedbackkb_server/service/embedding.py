"""Embedding provider (ISP Phase 7, Step 43, AP P5).

Config-driven, OFF by default (`FEEDBACKKB_EMBED=none`). When off, `embed()` returns
None for every text so callers transparently fall back to FTS/ILIKE/hash (P1-P4
behaviour). Adapters:
  - none   -> None (off)
  - openai -> text-embedding-3-small (1536)   [lazy SDK]
  - local  -> sentence-transformers all-MiniLM-L6-v2 (384)  [lazy import]

A process-local cache keyed by a content hash avoids re-embedding identical text.
"""

from __future__ import annotations

import hashlib
import os

_CACHE: dict[str, list[float]] = {}


def _key(text: str, adapter: str) -> str:
    return hashlib.sha256(f"{adapter}\x00{text}".encode()).hexdigest()


def _embed_openai(texts: list[str]) -> list[list[float]]:
    from openai import OpenAI  # lazy — only when adapter=openai

    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))
    model = os.environ.get("EMBED_MODEL", "text-embedding-3-small")
    resp = client.embeddings.create(model=model, input=texts)
    return [d.embedding for d in resp.data]


def _embed_local(texts: list[str]) -> list[list[float]]:
    from sentence_transformers import SentenceTransformer  # lazy

    model_name = os.environ.get("EMBED_MODEL", "all-MiniLM-L6-v2")
    model = SentenceTransformer(model_name)
    return [v.tolist() for v in model.encode(texts)]


def embed(texts: list[str], adapter: str | None = None) -> list[list[float] | None]:
    """Return one vector per text, or None per text when embeddings are off / fail.

    Never raises on provider error: logs nothing, returns None so intake/search keep
    working on the FTS fallback. Caller decides what to do with None.
    """
    name = adapter if adapter is not None else os.environ.get("FEEDBACKKB_EMBED", "none")
    if name == "none" or not texts:
        return [None] * len(texts)

    out: list[list[float] | None] = [None] * len(texts)
    todo: list[tuple[int, str]] = []
    for i, t in enumerate(texts):
        k = _key(t, name)
        if k in _CACHE:
            out[i] = _CACHE[k]
        else:
            todo.append((i, t))
    if not todo:
        return out
    try:
        vecs = (_embed_openai if name == "openai" else _embed_local)([t for _, t in todo])
    except Exception:
        return out  # provider unavailable -> all None for the misses (safe fallback)
    for (i, t), v in zip(todo, vecs):
        _CACHE[_key(t, name)] = v
        out[i] = v
    return out


def embed_one(text: str, adapter: str | None = None) -> list[float] | None:
    return embed([text], adapter)[0]


def to_pgvector(vec: list[float]) -> str:
    """Format a vector as a pgvector literal: '[1.0,2.0,...]'."""
    return "[" + ",".join(repr(float(x)) for x in vec) + "]"
