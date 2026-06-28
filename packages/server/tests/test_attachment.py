"""Step 8 — scan + attachment validate (no DB) + service (live DB)."""

import os

import pytest

from feedbackkb_server.adapters import get_storage
from feedbackkb_server.service import attachment_service as svc
from feedbackkb_server.service import scan

needs_db = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="DATABASE_URL not set (no live Postgres)",
)


# --- scan (no DB) ---

def test_scan_off_is_ready_even_for_eicar():
    assert scan.scan_status(scan.EICAR, "off") == "ready"


def test_scan_clamav_quarantines_eicar():
    # no clamd daemon -> falls back to signature check, still catches EICAR
    assert scan.scan_status(scan.EICAR, "clamav") == "quarantined"


def test_scan_clamav_clean_passes():
    assert scan.scan_status(b"\x89PNG harmless", "clamav") == "ready"


def test_scan_unknown_mode_raises():
    with pytest.raises(ValueError):
        scan.scan_status(b"x", "bogus")


# --- validate (no DB) ---

def test_validate_rejects_bad_mime():
    with pytest.raises(svc.AttachmentError) as ei:
        svc.validate(b"x", "application/zip")
    assert ei.value.status == 415


def test_validate_rejects_oversize():
    with pytest.raises(svc.AttachmentError) as ei:
        svc.validate(b"x" * (svc.MAX_SIZE + 1), "image/png")
    assert ei.value.status == 413


# --- service (DB) ---

@needs_db
def test_create_attachment_ready_and_no_public_url():
    from feedbackkb_server import db
    from feedbackkb_server.repo import system
    db.apply_migrations()
    with db.connect() as conn:
        system.register_system(conn, code="T_ATT", name="t")
        res = svc.create_attachment(
            conn, get_storage("local"), system="T_ATT",
            data=b"\x89PNG ok", mime="image/png", scan_mode="off",
        )
        url = svc.get_signed_url(conn, get_storage("local"), res.attachment_id, "T_ATT")
    assert res.status == "ready"
    assert "sig=" in url  # signed, not public


@needs_db
def test_cross_tenant_read_denied():
    from feedbackkb_server import db
    from feedbackkb_server.repo import system
    db.apply_migrations()
    storage = get_storage("local")
    with db.connect() as conn:
        system.register_system(conn, code="T_A", name="a")
        res = svc.create_attachment(conn, storage, system="T_A",
                                    data=b"x", mime="image/png", scan_mode="off")
        with pytest.raises(svc.AttachmentError) as ei:
            svc.get_signed_url(conn, storage, res.attachment_id, "T_B")
    assert ei.value.status == 403


@needs_db
def test_get_content_returns_bytes_and_acl():
    from feedbackkb_server import db
    from feedbackkb_server.repo import system
    db.apply_migrations()
    storage = get_storage("local")  # single instance → blob persists in memory
    with db.connect() as conn:
        system.register_system(conn, code="T_C", name="c")
        res = svc.create_attachment(conn, storage, system="T_C",
                                    data=b"\x89PNG-pixels", mime="image/png", scan_mode="off")
        data, mime = svc.get_content(conn, storage, res.attachment_id, "T_C")
        assert data == b"\x89PNG-pixels" and mime == "image/png"
        # cross-tenant read denied (same gate as signed url)
        with pytest.raises(svc.AttachmentError) as ei:
            svc.get_content(conn, storage, res.attachment_id, "T_OTHER")
    assert ei.value.status == 403
