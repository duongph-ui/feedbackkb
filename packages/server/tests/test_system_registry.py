"""Step 5 — app_key crypto (no DB) + register/rotate (live DB)."""

import os

import pytest

from feedbackkb_server.repo import system
from feedbackkb_server.security import appkey

needs_db = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="DATABASE_URL not set (no live Postgres)",
)


# --- crypto (no DB) ---

def test_generate_has_prefix_and_is_unique():
    a, b = appkey.generate(), appkey.generate()
    assert a.startswith("fbk_live_") and a != b


def test_hash_then_verify():
    raw = appkey.generate()
    h = appkey.hash_key(raw)
    assert h != raw and len(h) == 64
    assert appkey.verify(raw, h) is True
    assert appkey.verify("fbk_live_wrong", h) is False


def test_display_prefix_8_chars():
    raw = appkey.generate()
    assert appkey.display_prefix(raw) == raw[:8]


# --- register/rotate (DB) ---

@needs_db
def test_register_stores_hash_not_raw():
    from feedbackkb_server import db
    db.apply_migrations()
    with db.connect() as conn:
        res = system.register_system(conn, code="T_REG", name="Test")
        row = system.get_system(conn, "T_REG")
    assert res.app_key.startswith("fbk_live_")
    assert row["app_key_hash"] == appkey.hash_key(res.app_key)
    assert res.app_key not in (row["app_key_hash"], row["app_key_prefix"])  # raw never stored
    assert appkey.verify(res.app_key, row["app_key_hash"])


@needs_db
def test_rotate_invalidates_old_key():
    from feedbackkb_server import db
    db.apply_migrations()
    with db.connect() as conn:
        first = system.register_system(conn, code="T_ROT", name="Test")
        old_hash = system.get_system(conn, "T_ROT")["app_key_hash"]
        second = system.rotate_key(conn, "T_ROT")
        new_hash = system.get_system(conn, "T_ROT")["app_key_hash"]
    assert second.app_key != first.app_key
    assert new_hash != old_hash
    assert not appkey.verify(first.app_key, new_hash)
