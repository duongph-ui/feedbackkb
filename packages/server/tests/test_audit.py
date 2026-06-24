"""Step 9 — audit append-only helper."""

import os

import pytest

from feedbackkb_server.service import audit

needs_db = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="DATABASE_URL not set (no live Postgres)",
)


def test_actor_type_validated():
    # no DB needed: validation happens before any SQL
    with pytest.raises(ValueError):
        audit.log_event(None, feedback_id=None, actor_type="robot", action="x")


@needs_db
def test_log_event_inserts_with_correlation():
    from feedbackkb_server import db
    from feedbackkb_server.repo import system
    db.apply_migrations()
    with db.connect() as conn:
        system.register_system(conn, code="T_AUD", name="t")
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO fbk.feedback(system,message) VALUES ('T_AUD','m') RETURNING id"
            )
            fid = str(cur.fetchone()[0])
        conn.commit()
        eid = audit.log_event(
            conn, feedback_id=fid, actor_type="human", action="status_change",
            request_id="rq1", source_ip="1.2.3.4", old={"s": "new"}, new={"s": "triaged"},
        )
    assert eid


@needs_db
def test_event_update_blocked_by_trigger():
    from feedbackkb_server import db
    db.apply_migrations()
    with db.connect() as conn, pytest.raises(Exception):
        db.execute(conn, "UPDATE fbk.feedback_event SET action='x'")
