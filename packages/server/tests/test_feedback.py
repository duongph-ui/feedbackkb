"""Phase 2 backend — Step 11/12/13 (pure units + live-DB acceptance)."""

import os

import pytest

from feedbackkb_server.service import feedback_service as svc
from feedbackkb_server.service import secret_scan, status_machine

needs_db = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="DATABASE_URL not set (no live Postgres)",
)


# --- secret scan (Step 11 §7.5) ---

def test_secret_scan_redacts_api_key():
    red, has = secret_scan.scan("token is sk-abcdefghijklmnop1234 ok")
    assert has and "sk-" not in red and "[REDACTED]" in red


def test_secret_scan_catches_password_kv():
    red, has = secret_scan.scan("password=hunter2")
    assert has and "hunter2" not in red


def test_secret_scan_clean_text():
    red, has = secret_scan.scan("nút Gửi bị lỗi")
    assert has is False and red == "nút Gửi bị lỗi"


# --- symptom hash (Step 11/CL4) ---

def test_symptom_hash_normalises_whitespace_case():
    assert svc.symptom_hash("Lỗi  Tạo Phiếu") == svc.symptom_hash("lỗi tạo phiếu")


def test_symptom_hash_differs_on_content():
    assert svc.symptom_hash("a") != svc.symptom_hash("b")


# --- status machine (Step 13/CL2) ---

def test_legal_transition():
    assert status_machine.is_allowed("new", "triaged")
    assert status_machine.is_allowed("verified", "resolved")


def test_illegal_transition():
    assert not status_machine.is_allowed("new", "resolved")
    assert not status_machine.is_allowed("wontfix", "in_progress")


def test_requires_lesson_only_for_real_bug():
    assert status_machine.requires_lesson("bug", "high", "resolved")
    assert status_machine.requires_lesson("bug", "med", "resolved")
    assert not status_machine.requires_lesson("bug", "low", "resolved")
    assert not status_machine.requires_lesson("idea", "high", "resolved")
    assert not status_machine.requires_lesson("bug", "high", "triaged")


def test_create_rejects_empty_message():
    with pytest.raises(svc.FeedbackError) as ei:
        svc.create(None, system="X", message="   ")
    assert ei.value.status == 422


# --- live DB ---

@needs_db
def test_create_enqueues_triage_and_flags_secret():
    from feedbackkb_server import db
    from feedbackkb_server.repo import system
    db.apply_migrations()
    with db.connect() as conn:
        system.register_system(conn, code="T_FB", name="t")
        res = svc.create(conn, system="T_FB", message="lỗi + token sk-abcdefghij1234567890")
        full = svc.get(conn, res.id, "T_FB")
    assert res.has_secret is True
    assert any(t["stage"] == "triage" for t in full["agent_tasks"])
    assert "sk-" not in full["message"]


@needs_db
def test_transition_illegal_rejected():
    from feedbackkb_server import db
    from feedbackkb_server.repo import system
    db.apply_migrations()
    with db.connect() as conn:
        system.register_system(conn, code="T_TR", name="t")
        res = svc.create(conn, system="T_TR", message="m")
        with pytest.raises(svc.FeedbackError) as ei:
            svc.transition(conn, res.id, "resolved")
    assert ei.value.status == 409


@needs_db
def test_resolved_bug_requires_lesson():
    from feedbackkb_server import db
    from feedbackkb_server.repo import system
    db.apply_migrations()
    with db.connect() as conn:
        system.register_system(conn, code="T_CL2", name="t")
        res = svc.create(conn, system="T_CL2", message="bug")
        # walk to verified as a high bug
        with conn.cursor() as cur:
            cur.execute("UPDATE fbk.feedback SET type='bug', severity='high' WHERE id=%s",
                        (res.id,))
        conn.commit()
        svc.transition(conn, res.id, "triaged")
        svc.transition(conn, res.id, "in_progress")
        svc.transition(conn, res.id, "verified")
        with pytest.raises(svc.FeedbackError) as ei:
            svc.transition(conn, res.id, "resolved")  # no knowledge_ref yet
    assert ei.value.status == 412
