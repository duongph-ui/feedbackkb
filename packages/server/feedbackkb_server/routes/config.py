"""Privacy config routes (Step 20).

GET  /api/config  — public: widget reads denylist + consent before capturing.
PATCH /api/config — admin: tune denylist / retention / consent at runtime.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ..adapters import Identity
from ..security.deps import require_role
from ..service import privacy_config

router = APIRouter(prefix="/api/config", tags=["config"])


class ConfigPatch(BaseModel):
    denylist_routes: list[str] | None = None
    denylist_selectors: list[str] | None = None
    retention_days: int | None = None
    consent_text: str | None = None


@router.get("")
def get_config() -> dict:
    return privacy_config.get()


@router.patch("")
def patch_config(body: ConfigPatch, _: Identity = Depends(require_role("admin"))) -> dict:
    return privacy_config.update(body.model_dump(exclude_none=True))
