"""Settings — all config from ENV, zero secrets in code (§6.1).

`DATABASE_URL` is required (no default) so a misconfigured deploy fails loudly
at startup instead of half-working. Everything else has a safe default that
makes a standalone, no-Clevai build run (`local`/`keyword`/`none`).
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str  # required — startup fails if unset

    # adapter selection (Step 3)
    storage: Literal["local", "gcs", "s3"] = "local"
    search: Literal["keyword", "pgvector", "sepo"] = "keyword"
    auth: Literal["none", "appkey", "jwt"] = "none"
    knowledge: Literal["pg", "sepo"] = "pg"

    # semantic / AI (Phase 7, AP P5) — off-by-default; P1-P4 run on FTS+hash without these
    embed: Literal["none", "openai", "local"] = "none"
    embed_dim: int = 1536               # must match the embed adapter's model
    fixability_min: float = 0.6         # orchestrator: score >= -> auto, < -> need_human

    # auth (Step 6)
    fpa_jwt_secret: str = ""

    # zero-admin onboarding — let systems exist without an admin `register` call.
    # seed_systems: "CODE:Name,CODE2:Name2" upserted at startup (ops sets it once).
    # open_register: auto-create an unknown system on first feedback (trust-on-
    # first-use; internal/trusted networks only — leave OFF on public-facing APIs).
    seed_systems: str = ""
    open_register: bool = False

    # storage (Step 7)
    signed_url_ttl: int = 300
    gcs_bucket: str = ""
    s3_bucket: str = ""

    # attachment scan (Step 8) / anti-abuse (Step 10) / retention (Step 8/20)
    scan: Literal["clamav", "off"] = "off"
    captcha: Literal["turnstile", "off"] = "off"
    redis_url: str = ""
    attachment_retention_days: int = 90

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="",
        extra="ignore",
        # map FEEDBACKKB_STORAGE -> storage, DATABASE_URL -> database_url, etc.
        env_nested_delimiter=None,
    )


# explicit env aliases for the FEEDBACKKB_* names from .env.example
_ALIASES = {
    "storage": "FEEDBACKKB_STORAGE",
    "search": "FEEDBACKKB_SEARCH",
    "auth": "FEEDBACKKB_AUTH",
    "knowledge": "FEEDBACKKB_KNOWLEDGE",
    "scan": "FEEDBACKKB_SCAN",
    "captcha": "FEEDBACKKB_CAPTCHA",
    "seed_systems": "FEEDBACKKB_SEED_SYSTEMS",
    "open_register": "FEEDBACKKB_OPEN_REGISTER",
    "embed": "FEEDBACKKB_EMBED",
}


@lru_cache
def get_settings() -> Settings:
    import os

    overrides = {}
    for field, env in _ALIASES.items():
        if env in os.environ:
            overrides[field] = os.environ[env]
    return Settings(**overrides)
