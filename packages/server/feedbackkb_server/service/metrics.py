"""Knowledge metrics (Step 29, CL7-C).

capture-rate, resolved-with-lesson, hot lessons. Ratio math is pure-testable;
the source queries are DB-bound.
"""

from __future__ import annotations

import psycopg


def ratio(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


def resolved_with_lesson(conn: psycopg.Connection, system: str | None = None) -> dict:
    where = "WHERE type='bug' AND status='resolved'"
    params: list = []
    if system:
        where += " AND system=%s"
        params.append(system)
    with conn.cursor() as cur:
        cur.execute(f"SELECT count(*) FROM fbk.feedback {where}", params)
        total = cur.fetchone()[0]
        cur.execute(
            f"""SELECT count(*) FROM fbk.feedback f {where}
                 AND EXISTS (SELECT 1 FROM fbk.knowledge_ref k WHERE k.feedback_id=f.id)""",
            params,
        )
        with_lesson = cur.fetchone()[0]
    return {"total": total, "with_lesson": with_lesson, "rate": ratio(with_lesson, total)}


def hot_lessons(conn: psycopg.Connection, limit: int = 10) -> list[dict]:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT title, occurrence, system FROM fbk.knowledge_ref "
            "ORDER BY occurrence DESC LIMIT %s",
            (limit,),
        )
        return [dict(zip(("title", "occurrence", "system"), r)) for r in cur.fetchall()]
