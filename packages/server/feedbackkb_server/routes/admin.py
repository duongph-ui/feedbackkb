"""Admin routes — register/rotate a system (require admin role). Step 5/6.

The CLI (Step 21b) wraps these endpoints; this is the only place app_keys are
minted, and the raw key is returned once in the response body.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from .. import db
from ..adapters import Identity, get_storage
from ..config import get_settings
from ..repo import system
from ..security.deps import require_role
from ..service import gdpr

router = APIRouter(prefix="/api/admin", tags=["admin"])


class RegisterBody(BaseModel):
    code: str
    name: str
    org_id: str | None = None
    scopes: list[str] | None = None
    origin_allowlist: str | None = None


class RegisterResponse(BaseModel):
    code: str
    app_key: str          # raw — shown ONCE
    app_key_prefix: str


@router.post("/register", response_model=RegisterResponse)
def register(body: RegisterBody, _: Identity = Depends(require_role("admin"))):
    with db.connect() as conn:
        res = system.register_system(
            conn, code=body.code, name=body.name, org_id=body.org_id,
            scopes=body.scopes, origin_allowlist=body.origin_allowlist,
        )
    return RegisterResponse(code=res.code, app_key=res.app_key, app_key_prefix=res.app_key_prefix)


@router.post("/rotate/{code}", response_model=RegisterResponse)
def rotate(code: str, _: Identity = Depends(require_role("admin"))):
    with db.connect() as conn:
        res = system.rotate_key(conn, code)
    return RegisterResponse(code=res.code, app_key=res.app_key, app_key_prefix=res.app_key_prefix)


# --- GDPR (Step 13b) ---

def _storage():
    return get_storage(get_settings().storage)


@router.get("/export")
def export(system_code: str, user_email: str | None = None,
           _: Identity = Depends(require_role("admin"))):
    with db.connect() as conn:
        return gdpr.export(conn, system=system_code, user_email=user_email)


@router.delete("/feedback/{feedback_id}")
def delete_feedback(feedback_id: str, ident: Identity = Depends(require_role("admin"))):
    with db.connect() as conn:
        gdpr.delete_feedback(conn, _storage(), feedback_id, actor_id=ident.user)
    return {"ok": True}


@router.delete("/erase")
def erase(system_code: str, user_email: str, ident: Identity = Depends(require_role("admin"))):
    with db.connect() as conn:
        n = gdpr.erase_user(conn, _storage(), system=system_code, user_email=user_email)
    return {"erased": n}
