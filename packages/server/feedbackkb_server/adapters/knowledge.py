"""KnowledgeStore adapter — where lesson CONTENT lives (§5 #6).

Postgres always keeps the `knowledge_ref` index (link + dedupe key); this
adapter only owns the content body:
  - `pg`   -> fbk.knowledge_doc (self-host, no external service)
  - `sepo` -> sepo-mcp wiki (Clevai)   [impl in Step 22]

Step 3 ships the contract + an in-memory `pg`-shaped impl so the interface is
exercisable before the DB layer exists. Real DB-backed `PgKnowledgeStore` and
the `sepo` adapter arrive in Step 22.
"""

from __future__ import annotations

import abc
import json
import os
import urllib.parse
import urllib.request
import uuid
from dataclasses import dataclass


@dataclass
class Lesson:
    system: str
    title: str
    content: str
    symptom_hash: str = ""
    status: str = "draft"  # draft | trusted (§7.5)


class KnowledgeStore(abc.ABC):
    @abc.abstractmethod
    def put(self, lesson: Lesson) -> str:
        """Persist content, return a store_ref (knowledge_doc.id or wiki_path)."""

    @abc.abstractmethod
    def get(self, store_ref: str) -> Lesson | None: ...

    @abc.abstractmethod
    def search(self, query: str, system: str | None = None) -> list[dict]: ...


class InMemoryKnowledgeStore(KnowledgeStore):
    """Placeholder `pg`-shaped store. Step 22 swaps in fbk.knowledge_doc."""

    def __init__(self) -> None:
        self._docs: dict[str, Lesson] = {}

    def put(self, lesson: Lesson) -> str:
        ref = uuid.uuid4().hex
        self._docs[ref] = lesson
        return ref

    def get(self, store_ref: str) -> Lesson | None:
        return self._docs.get(store_ref)

    def search(self, query: str, system: str | None = None) -> list[dict]:
        ql = query.lower()
        out = []
        for ref, doc in self._docs.items():
            if system is not None and doc.system != system:
                continue
            if ql in doc.title.lower() or ql in doc.content.lower():
                out.append({"store_ref": ref, "title": doc.title, "system": doc.system})
        return out


class SepoKnowledgeStore(KnowledgeStore):
    """`sepo` adapter — lesson CONTENT lives in the SEPO wiki, reached over HTTP.

    Config via env (server-side only): SEPO_WIKI_URL (required), SEPO_TOKEN
    (optional bearer). `put` returns the wiki_path used as store_ref; PG still
    keeps the knowledge_ref index. Unconfigured use raises a clear error instead
    of the old bare NotImplementedError.
    """

    def __init__(self) -> None:
        self.base = os.environ.get("SEPO_WIKI_URL", "").rstrip("/")
        self.token = os.environ.get("SEPO_TOKEN", "")

    def _req(self, method: str, path: str, body: dict | None = None) -> dict:
        if not self.base:
            raise RuntimeError("sepo KnowledgeStore needs SEPO_WIKI_URL env")
        data = json.dumps(body).encode() if body is not None else None
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        req = urllib.request.Request(self.base + path, data=data, method=method, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as r:  # noqa: S310 (configured base URL)
            return json.loads(r.read().decode() or "{}")

    def put(self, lesson: Lesson) -> str:
        res = self._req("POST", "/wiki", {
            "system": lesson.system, "title": lesson.title, "content": lesson.content,
            "status": lesson.status, "symptom_hash": lesson.symptom_hash,
        })
        return res.get("wiki_path") or res.get("path") or res.get("store_ref", "")

    def get(self, store_ref: str) -> Lesson | None:
        try:
            res = self._req("GET", "/wiki?" + urllib.parse.urlencode({"path": store_ref}))
        except Exception:
            return None
        if not res:
            return None
        return Lesson(system=res.get("system", ""), title=res.get("title", ""),
                      content=res.get("content", ""), status=res.get("status", "draft"))

    def search(self, query: str, system: str | None = None) -> list[dict]:
        q = {"query": query}
        if system:
            q["system"] = system
        try:
            res = self._req("GET", "/wiki/search?" + urllib.parse.urlencode(q))
        except Exception:
            return []
        return res.get("results", []) if isinstance(res, dict) else (res or [])
