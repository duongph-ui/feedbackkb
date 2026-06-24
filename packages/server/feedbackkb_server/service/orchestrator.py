"""Auto-triage runtime (Gap 1 — the missing agent-team launcher, §3.3/§5 #7).

V1 roadmap: Conductor + Triage land first; Analyst + Fixer (real intelligence)
come later. So this runtime DETERMINISTICALLY drains the `triage` stage — exact +
near dedupe, then heuristic type/name/severity — moving feedback off `new` with no
live LLM. `analyze`/`fix`/`knowledge` stages need a real Claude agent, so they are
claimed and parked as `need_human` for the agent team / human gate to pick up.
"""

from __future__ import annotations

import psycopg

from ..adapters import get_search
from . import dedupe, embedding, feedback_service as fb, queue, triage


def auto_triage(conn: psycopg.Connection, feedback_id: str) -> dict:
    """Dedupe then heuristic-classify a single feedback. Returns a result dict."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT system, message, symptom_hash FROM fbk.feedback WHERE id=%s",
            (feedback_id,),
        )
        row = cur.fetchone()
    if row is None:
        return {"action": "missing"}
    system, message, sym = row

    # tier 1: exact dup
    exact = dedupe.find_exact(conn, system, sym, exclude_id=feedback_id)
    if exact:
        dedupe.mark_dup(conn, feedback_id, exact, actor_id="auto-triage", actor_type="system")
        return {"action": "dup", "dup_of": exact, "tier": "exact"}

    # tier 2a: semantic dup (Phase 7) — compute+store embedding, pgvector NN.
    # No-op when FEEDBACKKB_EMBED=none (embed returns None) -> falls through to FTS.
    vec = embedding.embed_one(message or "")
    dedupe.store_embedding(conn, feedback_id, vec)
    sem = dedupe.semantic_dup(conn, system, vec, exclude_id=feedback_id)
    if sem:
        dedupe.mark_dup(conn, feedback_id, sem, actor_id="auto-triage", actor_type="system")
        return {"action": "dup", "dup_of": sem, "tier": "semantic"}

    # tier 2b: near dup (FTS candidates ranked by search adapter)
    cands = dedupe.near_candidates(conn, system, message, feedback_id)
    near = dedupe.best_near_match(get_search("keyword"), message, cands)
    if near:
        dedupe.mark_dup(conn, feedback_id, near, actor_id="auto-triage", actor_type="system")
        return {"action": "dup", "dup_of": near, "tier": "near"}

    # not a dup -> heuristic classify + write
    g = triage.triage(message or "")
    fb.apply_triage(
        conn, feedback_id, type_=g.type, name=g.name, severity=g.severity,
        actor_id="auto-triage", actor_type="system",
    )
    # Phase 7 (Step 46): fixability gate -> auto-advance pipeline vs wait for human
    from ..config import get_settings
    from ..repo import knowledge as krepo
    from . import fixability
    has_lesson = krepo.find_ref_by_symptom(conn, system, sym) is not None
    fscore = fixability.score(
        lesson_match=has_lesson, grounding=has_lesson,
        dedupe_clear=True, severity_known=g.severity is not None,
    )
    auto = fixability.is_auto(fscore, get_settings().fixability_min)
    if auto:
        queue.enqueue(conn, feedback_id, "analyze")  # advance to Analyst stage
    return {"action": "triaged", "type": g.type, "name": g.name, "severity": g.severity,
            "fixability": fscore, "auto_advance": auto}


def run_once(conn: psycopg.Connection, agent: str = "conductor") -> dict | None:
    """Claim one runnable task and handle it. Returns the task dict (with result)
    or None when the queue is empty. Triage runs deterministically; richer stages
    park as need_human for the real agent team."""
    task = queue.claim(conn, agent)
    if task is None:
        return None
    if task["stage"] == "triage":
        res = auto_triage(conn, task["feedback_id"])
        queue.complete(conn, task["id"], result=res)
    else:
        # analyze / fix / knowledge need a real Claude agent + human gate
        queue.complete(
            conn, task["id"],
            result={"escalate": "needs Claude agent", "stage": task["stage"]},
            status="need_human",
        )
        res = {"action": "escalated", "stage": task["stage"]}
    return {**task, "result": res}


def drain(conn: psycopg.Connection, agent: str = "conductor", max_tasks: int = 1000) -> int:
    """Process runnable tasks until the queue is empty (or max_tasks). Returns count."""
    n = 0
    while n < max_tasks and run_once(conn, agent) is not None:
        n += 1
    return n
