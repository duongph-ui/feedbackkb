"""Captcha verification for anonymous submit (§7.1, Step 10).

Modes (FEEDBACKKB_CAPTCHA):
  - off       -> always passes (authenticated/self-host-open default).
  - turnstile -> Cloudflare Turnstile server-side siteverify.

`verifier` is injectable so tests don't hit the network.
"""

from __future__ import annotations

from typing import Callable

TURNSTILE_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


def verify(token: str | None, mode: str = "off", *,
           secret: str = "", verifier: Callable[[str, str], bool] | None = None) -> bool:
    if mode == "off":
        return True
    if mode == "turnstile":
        if not token:
            return False
        v = verifier or _turnstile_verify
        return v(token, secret)
    raise ValueError(f"unknown captcha mode {mode!r}")


def _turnstile_verify(token: str, secret: str) -> bool:
    import httpx

    try:
        r = httpx.post(TURNSTILE_URL, data={"secret": secret, "response": token}, timeout=5)
        return bool(r.json().get("success"))
    except Exception:
        return False
