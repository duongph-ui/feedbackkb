"""Step 13b — GDPR export/delete/erase + blob cascade (live DB)."""

import os

import pytest

needs_db = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="DATABASE_URL not set (no live Postgres)",
)


@needs_db
def test_delete_cascades_attachment_and_keeps_audit():
    from feedbackkb_server import db
    from feedbackkb_server.adapters import get_storage
    from feedbackkb_server.repo import system
    from feedbackkb_server.service import attachment_service, feedback_service, gdpr

    db.apply_migrations()
    storage = get_storage("local")
    with db.connect() as conn:
        system.register_system(conn, code="T_GD", name="t")
        res = feedback_service.create(conn, system="T_GD", message="m")
        att = attachment_service.create_attachment(
            conn, storage, system="T_GD", data=b"x", mime="image/png", scan_mode="off",
        )
        with conn.cursor() as cur:
            cur.execute("UPDATE fbk.feedback_attachment SET feedback_id=%s WHERE id=%s",
                        (res.id, att.attachment_id))
        conn.commit()

        gdpr.delete_feedback(conn, storage, res.id)

        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM fbk.feedback WHERE id=%s", (res.id,))
            assert cur.fetchone()[0] == 0
            cur.execute("SELECT count(*) FROM fbk.feedback_attachment WHERE id=%s",
                        (att.attachment_id,))
            assert cur.fetchone()[0] == 0  # cascade
            cur.execute("SELECT count(*) FROM fbk.feedback_event WHERE action='delete'")
            assert cur.fetchone()[0] >= 1  # audit kept (SET NULL)


@needs_db
def test_export_tenant_scoped():
    from feedbackkb_server import db
    from feedbackkb_server.repo import system
    from feedbackkb_server.service import feedback_service, gdpr

    db.apply_migrations()
    with db.connect() as conn:
        system.register_system(conn, code="T_EXA", name="a")
        system.register_system(conn, code="T_EXB", name="b")
        feedback_service.create(conn, system="T_EXA", message="from A")
        feedback_service.create(conn, system="T_EXB", message="from B")
        dump = gdpr.export(conn, system="T_EXA")
    msgs = [f["message"] for f in dump["feedback"]]
    assert "from A" in msgs and "from B" not in msgs
