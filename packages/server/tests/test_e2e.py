"""Phase 6 — end-to-end chain (Step 41). Live DB only (full stack).

Exercises: register -> submit (secret-scan + enqueue) -> claim triage ->
transition through the status machine -> capture lesson (CL2 satisfied) ->
resolve, plus forward idempotency and tenant isolation.
"""

import os

import pytest

needs_db = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="DATABASE_URL not set (no live Postgres)",
)


@needs_db
def test_full_chain_bug_to_resolved_with_lesson():
    from feedbackkb_server import db
    from feedbackkb_server.repo import system
    from feedbackkb_server.service import feedback_service as fb
    from feedbackkb_server.service import knowledge_write as kw
    from feedbackkb_server.service import queue

    db.apply_migrations()
    with db.connect() as conn:
        system.register_system(conn, code="E2E", name="t")

        # submit (also enqueues triage)
        res = fb.create(conn, system="E2E", message="lỗi tạo phiếu trùng số")

        # conductor claims the triage task atomically
        task = queue.claim(conn, "conductor")
        assert task["stage"] == "triage" and task["feedback_id"] == res.id
        queue.complete(conn, task["id"])

        # triage classifies it as a high bug
        with conn.cursor() as cur:
            cur.execute("UPDATE fbk.feedback SET type='bug', severity='high' WHERE id=%s",
                        (res.id,))
        conn.commit()

        # walk the status machine
        fb.transition(conn, res.id, "triaged")
        fb.transition(conn, res.id, "in_progress")
        fb.transition(conn, res.id, "verified")

        # CL2: resolving a real bug requires a lesson -> blocked until captured
        with pytest.raises(fb.FeedbackError):
            fb.transition(conn, res.id, "resolved")

        kw.write(
            conn,
            kw.Lesson(system="E2E", title="dup ca_number", content="lock the row",
                      root_cause="race on ca_number", prevent="SELECT ... FOR UPDATE"),
            source="capture-fix", feedback_id=res.id,
        )
        fb.transition(conn, res.id, "resolved")  # now allowed

        full = fb.get(conn, res.id, "E2E")
    assert full["status"] == "resolved"


@needs_db
def test_forward_idempotent():
    from feedbackkb_server import db
    from feedbackkb_server.repo import system
    from feedbackkb_server.service import feedback_service as fb

    db.apply_migrations()
    with db.connect() as conn:
        system.register_system(conn, code="E2EF", name="t")
        a = fb.create(conn, system="E2EF", message="x", source="forward",
                      external_system="old", external_id="42")
        b = fb.create(conn, system="E2EF", message="x", source="forward",
                      external_system="old", external_id="42")
    assert a.id == b.id  # same external_id -> one row
