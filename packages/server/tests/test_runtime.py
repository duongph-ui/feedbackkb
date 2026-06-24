"""Gap 1-4: triage heuristic + auto-triage runtime + triage write + sepo adapter."""

import os

import pytest

from feedbackkb_server.adapters import SepoKnowledgeStore, get_knowledge
from feedbackkb_server.service import triage

needs_db = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="DATABASE_URL not set (no live Postgres)",
)


# --- Gap 2: heuristic triage (no DB) ---

def test_classify_type():
    assert triage.classify_type("Lỗi tạo phiếu trùng số") == "bug"
    assert triage.classify_type("Nên có nút export Excel") == "idea"
    assert triage.classify_type("Làm sao để đổi mật khẩu") == "question"


def test_guess_severity():
    assert triage.guess_severity("app crash mất dữ liệu", "bug") == "crit"
    assert triage.guess_severity("lỗi sai số tiền", "bug") == "high"
    assert triage.guess_severity("Nên có dark mode", "idea") == "low"


def test_make_name_truncates():
    n = triage.make_name("x" * 200)
    assert len(n) <= 60 and n.endswith("…")
    assert triage.make_name("Dòng đầu.\nDòng hai") == "Dòng đầu"


# --- Gap 4: sepo adapter (no network) ---

def test_sepo_adapter_registered_and_requires_env():
    store = get_knowledge("sepo")
    assert isinstance(store, SepoKnowledgeStore)
    store.base = ""  # force unconfigured -> clear error, not bare NotImplementedError
    with pytest.raises(RuntimeError, match="SEPO_WIKI_URL"):
        store._req("POST", "/wiki", {})


# --- Gap 1+2: auto-triage runtime (DB) ---

@needs_db
def test_auto_triage_classifies_and_dedupes():
    from feedbackkb_server import db
    from feedbackkb_server.repo import system
    from feedbackkb_server.service import feedback_service as fb, orchestrator
    db.apply_migrations()
    with db.connect() as conn:
        system.register_system(conn, code="T_RT", name="t")
        a = fb.create(conn, system="T_RT", message="Lỗi tạo phiếu trùng số nghiêm trọng")
        res = orchestrator.auto_triage(conn, a.id)
        assert res["action"] == "triaged" and res["type"] == "bug"
        # row got type/name/severity + status triaged + audit event
        got = fb.get(conn, a.id, requester_system=None)
        assert got["type"] == "bug" and got["status"] == "triaged"
        assert any(e["action"] == "triage" for e in got["events"])
        # identical feedback -> exact dup
        b = fb.create(conn, system="T_RT", message="Lỗi tạo phiếu trùng số nghiêm trọng")
        res2 = orchestrator.auto_triage(conn, b.id)
        assert res2["action"] == "dup" and res2["dup_of"] == a.id


@needs_db
def test_run_once_drains_triage_then_parks_richer_stages():
    from feedbackkb_server import db
    from feedbackkb_server.repo import system
    from feedbackkb_server.service import feedback_service as fb, orchestrator, queue
    db.apply_migrations()
    with db.connect() as conn:
        system.register_system(conn, code="T_RUN", name="t")
        fb.create(conn, system="T_RUN", message="màn hình trắng khi bấm lưu")  # enqueues triage
        task = orchestrator.run_once(conn)
        assert task is not None and task["stage"] == "triage"
        assert task["result"]["action"] in ("triaged", "dup")
        # enqueue a richer stage -> parked need_human
        fid = task["feedback_id"]
        queue.enqueue(conn, fid, "fix")
        t2 = orchestrator.run_once(conn)
        assert t2["stage"] == "fix" and t2["result"]["action"] == "escalated"
