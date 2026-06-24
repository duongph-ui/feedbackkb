"""Step `knowledge-write` (KW) — dedupe + trust + secret-scan (Step 23, CL4/CL7/§7.5).

Shared by Fixer (agent-authored -> draft) and /capture-fix (dev-approved ->
trusted). Filters noise, dedupes by symptom_hash (bump occurrence instead of
creating a duplicate), scrubs secrets, then writes content via the configured
KnowledgeStore (pg -> knowledge_doc; sepo -> wiki) while PG always keeps the
knowledge_ref index.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

import psycopg

from ..repo import knowledge as krepo
from . import secret_scan

TRUSTED_SOURCES = {"capture-fix"}  # dev-authored + approved


@dataclass
class Lesson:
    system: str
    title: str
    content: str
    category: str = "general"
    prevent: str = ""
    root_cause: str = ""


def trust_for_source(source: str) -> str:
    """agent-authored -> draft (needs human review); dev capture-fix -> trusted."""
    return "trusted" if source in TRUSTED_SOURCES else "draft"


def symptom_hash(title: str, root_cause: str = "") -> str:
    key = re.sub(r"\s+", " ", f"{title} {root_cause}".strip().lower())
    return hashlib.sha256(key.encode()).hexdigest()


def should_keep(lesson: Lesson) -> bool:
    """CL7-B: drop trivial lessons (typo/format, no prevention value)."""
    rc = lesson.root_cause.lower()
    if any(w in rc for w in ("typo", "format", "whitespace")) and not lesson.prevent:
        return False
    if not lesson.prevent.strip():
        return False
    return True


def slugify(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:64] or "lesson"


def write(
    conn: psycopg.Connection,
    lesson: Lesson,
    *,
    source: str,
    feedback_id: str | None = None,
    knowledge_adapter: str = "pg",
) -> dict:
    """Returns {action: 'created'|'bumped'|'skipped', ref_id?, store_ref?}."""
    if not should_keep(lesson):
        return {"action": "skipped", "reason": "trivial/no-prevention"}

    # scrub secrets from content before persisting (§7.5)
    content, _ = secret_scan.scan(lesson.content)
    sh = symptom_hash(lesson.title, lesson.root_cause)

    existing = krepo.find_ref_by_symptom(conn, lesson.system, sh)
    if existing:
        krepo.bump_occurrence(conn, existing["id"])
        return {"action": "bumped", "ref_id": existing["id"], "store_ref": existing["store_ref"]}

    if knowledge_adapter == "pg":
        store_ref = krepo.insert_doc(
            conn, system=lesson.system, slug=slugify(lesson.title), content=content
        )
        # Phase 7: store embedding for semantic search (no-op when embeddings off)
        from . import embedding
        vec = embedding.embed_one(content)
        if vec is not None:
            krepo.set_doc_embedding(conn, store_ref, embedding.to_pgvector(vec))
    elif knowledge_adapter == "sepo":
        from ..adapters import Lesson as StoreLesson, get_knowledge
        store = get_knowledge("sepo")
        store_ref = store.put(StoreLesson(
            system=lesson.system, title=lesson.title, content=content,
            symptom_hash=sh, status=trust_for_source(source),
        ))
    else:
        raise ValueError(f"unknown knowledge adapter {knowledge_adapter!r}")

    ref_id = krepo.insert_ref(
        conn, feedback_id=feedback_id, system=lesson.system, store_ref=store_ref,
        title=lesson.title, status=trust_for_source(source), symptom_hash=sh,
    )
    return {"action": "created", "ref_id": ref_id, "store_ref": store_ref}


def link_existing(
    conn: psycopg.Connection, *, feedback_id: str, system: str, store_ref: str, title: str,
) -> str:
    """Triage links a feedback to an existing lesson (Step 27)."""
    return krepo.insert_ref(
        conn, feedback_id=feedback_id, system=system, store_ref=store_ref,
        title=title, status="trusted",
    )
