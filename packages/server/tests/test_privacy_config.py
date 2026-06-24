"""Step 20 — privacy config service + route (no DB)."""

from fastapi.testclient import TestClient

from feedbackkb_server.adapters import Identity
from feedbackkb_server.app import create_app
from feedbackkb_server.security.deps import get_identity
from feedbackkb_server.service import privacy_config


def test_defaults_then_update():
    privacy_config.reset()
    base = privacy_config.get()
    assert base["denylist_routes"] == []
    updated = privacy_config.update({"denylist_routes": ["/payroll"], "retention_days": 30})
    assert updated["denylist_routes"] == ["/payroll"]
    assert updated["retention_days"] == 30
    assert privacy_config.get()["denylist_routes"] == ["/payroll"]


def test_update_ignores_unknown_keys():
    privacy_config.reset()
    out = privacy_config.update({"evil": "x", "consent_text": "hi"})
    assert "evil" not in out and out["consent_text"] == "hi"


def test_get_config_public():
    privacy_config.reset()
    c = TestClient(create_app())
    r = c.get("/api/config")
    assert r.status_code == 200
    assert "denylist_routes" in r.json()


def test_patch_requires_admin():
    privacy_config.reset()
    app = create_app()
    app.dependency_overrides[get_identity] = lambda: Identity(role="viewer", scopes=["read"])
    c = TestClient(app)
    assert c.patch("/api/config", json={"retention_days": 10}).status_code == 403

    app.dependency_overrides[get_identity] = lambda: Identity(role="admin", scopes=["read"])
    c2 = TestClient(app)
    assert c2.patch("/api/config", json={"retention_days": 10}).status_code == 200
