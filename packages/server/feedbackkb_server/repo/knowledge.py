"""knowledge_ref index + knowledge_doc (pg) repository (Step 22).

knowledge_ref is the always-present pointer (link feedback<->lesson + dedupe key).
knowledge_doc holds content only when the KnowledgeStore adapter is `pg`.
"""

from __future__ import annotations

import psycopg


def insert_doc(conn: psycopg.Connection, *, system: str, slug: str, content: str) -> str:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO fbk.knowledge_doc(system, slug, content) VALUES (%s,%s,%s) RETURNING id",
            (system, slug, content),
        )
        doc_id = str(cur.fetchone()[0])
    conn.commit()
    return doc_id


def get_doc(conn: psycopg.Connection, doc_id: str) -> dict | None:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, system, slug, content, version FROM fbk.knowledge_doc WHERE id=%s",
            (doc_id,),
        )
        row = cur.fetchone()
    if row is None:
        return None
    return dict(zip(("id", "system", "slug", "content", "version"), row))


def set_doc_embedding(conn: psycopg.Connection, doc_id: str, vec_literal: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE fbk.knowledge_doc SET embedding=%s::vector WHERE id=%s",
            (vec_literal, doc_id),
        )
    conn.commit()


def search_docs_semantic(conn: psycopg.Connection, *, system: str | None,
                         query_vec: str, limit: int = 10) -> list[dict]:
    """Phase 7 (Step 45): rank lessons by pgvector cosine distance on doc embeddings,
    joined to the knowledge_ref index. Used when FEEDBACKKB_EMBED != none."""
    sys_clause = "AND r.system = %s" if system else ""
    params: list = [query_vec]
    if system:
        params.append(system)
    params += [query_vec, min(limit, 50)]
    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT r.id, r.system, r.store_ref, r.title, r.status, r.occurrence,
                   left(coalesce(d.content,''), 280) AS snippet
              FROM fbk.knowledge_doc d
              JOIN fbk.knowledge_ref r ON r.store_ref = d.id::text
             WHERE d.embedding IS NOT NULL {sys_clause}
             ORDER BY d.embedding <=> %s::vector
             LIMIT %s
            """,
            params,
        )
        rows = cur.fetchall()
    cols = ("id", "system", "store_ref", "title", "status", "occurrence", "snippet")
    return [dict(zip(cols, r)) for r in rows]


def find_ref_by_symptom(conn: psycopg.Connection, system: str, symptom_hash: str) -> dict | None:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, store_ref, occurrence FROM fbk.knowledge_ref "
            "WHERE system=%s AND symptom_hash=%s LIMIT 1",
            (system, symptom_hash),
        )
        row = cur.fetchone()
    if row is None:
        return None
    return dict(zip(("id", "store_ref", "occurrence"), row))


def insert_ref(
    conn: psycopg.Connection, *, feedback_id: str | None, system: str, store_ref: str,
    title: str, kind: str = "lesson", status: str = "draft", symptom_hash: str = "",
) -> str:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO fbk.knowledge_ref
                (feedback_id, system, store_ref, title, kind, status, symptom_hash)
            VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id
            """,
            (feedback_id, system, store_ref, title, kind, status, symptom_hash),
        )
        ref_id = str(cur.fetchone()[0])
    conn.commit()
    return ref_id


def search_refs(conn: psycopg.Connection, *, system: str | None, query: str,
                limit: int = 10) -> list[dict]:
    """Keyword search over knowledge_ref + joined doc content (system-scoped if given).

    Plain ILIKE on title + doc content — enough for the pg KnowledgeStore. The
    pgvector/sepo adapters can override this later; the REST contract stays the same.
    """
    clauses = ["(r.title ILIKE %s OR d.content ILIKE %s)"]
    like = f"%{query}%"
    params: list = [like, like]
    if system:
        clauses.append("r.system = %s")
        params.append(system)
    where = " AND ".join(clauses)
    params.append(min(limit, 50))
    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT r.id, r.system, r.store_ref, r.title, r.status, r.occurrence,
                   left(coalesce(d.content,''), 280) AS snippet
              FROM fbk.knowledge_ref r
              LEFT JOIN fbk.knowledge_doc d ON d.id::text = r.store_ref
             WHERE {where}
             ORDER BY r.occurrence DESC, r.created_at DESC
             LIMIT %s
            """,
            params,
        )
        rows = cur.fetchall()
    cols = ("id", "system", "store_ref", "title", "status", "occurrence", "snippet")
    return [dict(zip(cols, r)) for r in rows]


def bump_occurrence(conn: psycopg.Connection, ref_id: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE fbk.knowledge_ref SET occurrence = occurrence + 1 WHERE id=%s", (ref_id,)
        )
    conn.commit()


def set_status(conn: psycopg.Connection, ref_id: str, status: str) -> None:
    with conn.cursor() as cur:
        cur.execute("UPDATE fbk.knowledge_ref SET status=%s WHERE id=%s", (status, ref_id))
    conn.commit()
