"""Runtime privacy config (§7.2, Step 20).

Admin-tunable denylist (routes + CSS selectors), attachment retention, and the
consent text the widget shows. In-process store seeded from Settings; a DB-backed
table can replace `_STATE` later without changing the route contract.
"""

from __future__ import annotations

from .. import config

_STATE: dict | None = None


def _defaults() -> dict:
    try:
        retention = config.get_settings().attachment_retention_days
    except Exception:
        retention = 90  # settings unavailable (e.g. DATABASE_URL unset) -> safe default
    return {
        "denylist_routes": [],
        "denylist_selectors": [],
        "retention_days": retention,
        "consent_text": "Ảnh màn hình sẽ được gửi kèm phản hồi của bạn.",
    }


def get() -> dict:
    global _STATE
    if _STATE is None:
        _STATE = _defaults()
    return dict(_STATE)


def update(patch: dict) -> dict:
    cur = get()
    allowed = {"denylist_routes", "denylist_selectors", "retention_days", "consent_text"}
    for k, v in patch.items():
        if k in allowed and v is not None:
            cur[k] = v
    globals()["_STATE"] = cur
    return dict(cur)


def reset() -> None:
    globals()["_STATE"] = None
