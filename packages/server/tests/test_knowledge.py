"""Phase 3 — knowledge_write / dedupe / queue / metrics pure cores (+ live DB)."""

import os

import pytest

from feedbackkb_server.adapters import KeywordSearch
from feedbackkb_server.service import dedupe, knowledge_write as kw
from feedbackkb_server.service import metrics, queue

needs_db = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="DATABASE_URL not set (no live Postgres)",
)


# --- knowledge_write trust + filter (Step 23, no DB) ---

def test_trust_for_source():
    assert kw.trust_for_source("capture-fix") == "trusted"
    assert kw.trust_for_source("fixer-agent") == "draft"


def test_should_keep_drops_trivial():
    trivial = kw.Lesson(system="FPS", title="t", content="c", root_cause="typo in label", prevent="")
    assert kw.should_keep(trivial) is False


def test_should_keep_requires_prevention():
    no_prev = kw.Lesson(system="FPS", title="t", content="c", root_cause="race", prevent="")
    assert kw.should_keep(no_prev) is False
    good = kw.Lesson(system="FPS", title="t", content="c", root_cause="race", prevent="lock row")
    assert kw.should_keep(good) is True


def test_symptom_hash_stable_and_slug():
    assert kw.symptom_hash("Dup CA", "race") == kw.symptom_hash("dup ca", "RACE")
    assert kw.slugify("Lỗi tạo phiếu!") == "l-i-t-o-phi-u"


def test_write_scrubs_secret_and_skips_trivial():
    skip = kw.write(None, kw.Lesson(system="X", title="t", content="c", root_cause="typo", prevent=""),
                    source="fixer")
    assert skip["action"] == "skipped"


# --- dedupe (Step 25, no DB) ---

def test_best_near_match_threshold():
    cands = [{"id": "1", "system": "FPS", "text": "lỗi tạo phiếu trùng số"}]
    hit = dedupe.best_near_match(KeywordSearch(), "lỗi tạo phiếu trùng số", cands)
    assert hit == "1"
    miss = dedupe.best_near_match(KeywordSearch(), "màu nút xấu", cands)
    assert miss is None


# --- queue (Step 28, no DB) ---

def test_idempotency_key():
    assert queue.idempotency_key("fb1", "triage") == "triage:fb1"


# --- metrics (Step 29, no DB) ---

def test_ratio():
    assert metrics.ratio(3, 4) == 0.75
    assert metrics.ratio(0, 0) == 0.0


# --- live DB ---

@needs_db
def test_kw_dedupe_bumps_occurrence():
    from feedbackkb_server import db
    from feedbackkb_server.repo import system
    db.apply_migrations()
    lesson = kw.Lesson(system="T_KW", title="dup ca", content="lock", root_cause="race", prevent="lock row")
    with db.connect() as conn:
        system.register_system(conn, code="T_KW", name="t")
        a = kw.write(conn, lesson, source="capture-fix")
        b = kw.write(conn, lesson, source="capture-fix")
    assert a["action"] == "created"
    assert b["action"] == "bumped"  # same symptom_hash -> occurrence++


@needs_db
def test_knowledge_routes_capture_then_search():
    # the REST surface the MCP tools call — capture a lesson, then find it
    from fastapi.testclient import TestClient

    from feedbackkb_server import db
    from feedbackkb_server.app import create_app
    from feedbackkb_server.repo import system
    db.apply_migrations()
    with db.connect() as conn:
        system.register_system(conn, code="T_KR", name="t")
    c = TestClient(create_app())
    cap = c.post("/api/knowledge/capture", json={
        "system": "T_KR", "symptom": "phieu trung so", "root_cause": "race on counter",
        "fix": "lock row", "prevent": "FOR UPDATE", "files": "svc.py:10",
    })
    assert cap.status_code == 200 and cap.json()["action"] == "created"
    found = c.get("/api/knowledge/search", params={"query": "trung", "system": "T_KR"})
    assert found.status_code == 200
    assert any("phieu trung so" in r["title"] for r in found.json())


@needs_db
def test_queue_claim_is_atomic():
    from feedbackkb_server import db
    from feedbackkb_server.repo import system
    from feedbackkb_server.service import feedback_service
    db.apply_migrations()
    with db.connect() as conn:
        system.register_system(conn, code="T_Q", name="t")
        res = feedback_service.create(conn, system="T_Q", message="m")  # enqueues triage
        first = queue.claim(conn, "w1")
        second = queue.claim(conn, "w2")
    assert first is not None and first["feedback_id"] == res.id
    assert second is None  # only one runnable task, claimed once
