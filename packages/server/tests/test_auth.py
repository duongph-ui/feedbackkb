"""Step 6 — jwt/appkey adapters + scope/role/tenant guards (no DB needed)."""

import jwt
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from feedbackkb_server.adapters import AppKeyAuth, AuthError, Identity, JwtAuth
from feedbackkb_server.security import appkey
from feedbackkb_server.security.deps import get_identity, require_role, require_scope, require_tenant

SECRET = "test-secret-at-least-32-bytes-long-xx"


# --- JWT adapter ---

def test_jwt_valid():
    token = jwt.encode({"email": "a@b.com", "role": "admin", "system": "FPS"}, SECRET, "HS256")
    ident = JwtAuth(SECRET).verify({"Authorization": f"Bearer {token}"})
    assert ident.user == "a@b.com" and ident.role == "admin" and ident.system == "FPS"


def test_jwt_bad_signature_raises():
    token = jwt.encode({"email": "a@b.com"}, "wrong-secret-also-32-bytes-long-xxxxx", "HS256")
    with pytest.raises(AuthError) as ei:
        JwtAuth(SECRET).verify({"Authorization": f"Bearer {token}"})
    assert ei.value.status == 401


def test_jwt_absent_returns_none():
    assert JwtAuth(SECRET).verify({}) is None


# --- app_key adapter (fake lookup, no DB) ---

def _row(raw, **over):
    base = {
        "app_key_hash": appkey.hash_key(raw),
        "scopes": ["submit"],
        "origin_allowlist": None,
        "system": "FPS",
        "org_id": "o1",
        "active": True,
    }
    base.update(over)
    return base


def test_appkey_valid_scope_submit():
    raw = appkey.generate()
    a = AppKeyAuth(lambda p: _row(raw))
    ident = a.verify({"X-App-Key": raw})
    assert ident.system == "FPS" and ident.scopes == ["submit"]


def test_appkey_invalid_key_raises():
    raw = appkey.generate()
    a = AppKeyAuth(lambda p: _row("fbk_live_other"))
    with pytest.raises(AuthError):
        a.verify({"X-App-Key": raw})


def test_appkey_origin_blocked():
    raw = appkey.generate()
    a = AppKeyAuth(lambda p: _row(raw, origin_allowlist="trusted.com"))
    with pytest.raises(AuthError) as ei:
        a.verify({"X-App-Key": raw, "Origin": "https://evil.com"})
    assert ei.value.status == 403


# --- guards via a tiny app ---

def _app_with(identity: Identity):
    app = FastAPI()
    app.dependency_overrides[get_identity] = lambda: identity

    @app.get("/needs-read")
    def r(_: Identity = Depends(require_scope("read"))):
        return {"ok": True}

    @app.get("/needs-admin")
    def a(_: Identity = Depends(require_role("admin"))):
        return {"ok": True}

    return TestClient(app)


def test_scope_guard_blocks_submit_only_key():
    c = _app_with(Identity(scopes=["submit"]))
    assert c.get("/needs-read").status_code == 403


def test_role_guard_blocks_viewer():
    c = _app_with(Identity(role="viewer", scopes=["read"]))
    assert c.get("/needs-admin").status_code == 403
    c2 = _app_with(Identity(role="admin", scopes=["read"]))
    assert c2.get("/needs-admin").status_code == 200


def test_tenant_guard_blocks_cross_system():
    import fastapi

    with pytest.raises(fastapi.HTTPException) as ei:
        require_tenant(Identity(system="FPS"), "HRMS")
    assert ei.value.status_code == 403
    # same system: allowed (no raise)
    require_tenant(Identity(system="FPS"), "FPS")
