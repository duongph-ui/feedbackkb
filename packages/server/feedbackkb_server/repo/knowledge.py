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
