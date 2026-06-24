"""app_key generation + hashing (§7.1).

The raw key is returned to the caller exactly once at registration; the DB only
ever stores `sha256(key)` + an 8-char prefix for display. There is NO code path
that writes the raw key, which the tests assert.
"""

from __future__ import annotations

import hashlib
import secrets

PREFIX = "fbk_live_"
PREFIX_LEN = 8  # chars stored for display/identification


def generate() -> str:
    """Return a fresh raw key, e.g. 'fbk_live_<43 url-safe chars>'."""
    return PREFIX + secrets.token_urlsafe(32)


def hash_key(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def verify(raw: str, stored_hash: str) -> bool:
    return secrets.compare_digest(hash_key(raw), stored_hash)


def display_prefix(raw: str) -> str:
    return raw[:PREFIX_LEN]
