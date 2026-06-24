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
