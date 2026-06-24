"""Step 2 — FastAPI skeleton + config + request_id."""

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from feedbackkb_server.app import create_app
from feedbackkb_server.config import Settings
from feedbackkb_server.middleware import REQUEST_ID_HEADER


@pytest.fixture
def client():
    return TestClient(create_app())


def test_healthz_ok(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_settings_requires_database_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)  # no .env fallback in test


def test_request_id_generated(client):
    r = client.get("/healthz")
    assert r.headers.get(REQUEST_ID_HEADER)


def test_request_id_reused_from_client(client):
    r = client.get("/healthz", headers={REQUEST_ID_HEADER: "abc123"})
    assert r.headers[REQUEST_ID_HEADER] == "abc123"
