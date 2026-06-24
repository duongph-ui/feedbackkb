"""Step 10 — rate limit + captcha + observability (no DB)."""

import pytest
from fastapi.testclient import TestClient

from feedbackkb_server import observability as obs
from feedbackkb_server.app import create_app
from feedbackkb_server.service import captcha
from feedbackkb_server.service.ratelimit import RateLimiter


# --- rate limiter ---

def test_limiter_blocks_over_limit():
    t = [0.0]
    rl = RateLimiter(limit=2, window_s=60, clock=lambda: t[0])
    assert rl.allow("k") is True
    assert rl.allow("k") is True
    assert rl.allow("k") is False  # 3rd in window


def test_limiter_window_resets():
    t = [0.0]
    rl = RateLimiter(limit=1, window_s=10, clock=lambda: t[0])
    assert rl.allow("k") is True
    assert rl.allow("k") is False
    t[0] = 11.0
    assert rl.allow("k") is True  # window passed


def test_limiter_key_separates_tenants():
    assert RateLimiter.key("1.1.1.1", "FPS", "fbk_live") != RateLimiter.key("1.1.1.1", "HRMS", "fbk_live")


# --- captcha ---

def test_captcha_off_passes():
    assert captcha.verify(None, "off") is True


def test_captcha_turnstile_requires_token():
    assert captcha.verify(None, "turnstile") is False


def test_captcha_turnstile_uses_verifier():
    assert captcha.verify("tok", "turnstile", verifier=lambda t, s: True) is True
    assert captcha.verify("tok", "turnstile", verifier=lambda t, s: False) is False


def test_captcha_unknown_mode_raises():
    with pytest.raises(ValueError):
        captcha.verify("x", "hcaptcha")


# --- observability ---

def test_metrics_endpoint_exposes_counters():
    c = TestClient(create_app())
    obs.RATE_LIMITED.inc()
    r = c.get("/metrics")
    assert r.status_code == 200
    assert b"fbk_rate_limited_total" in r.content
    assert b"fbk_request_latency_seconds" in r.content
