"""Auth dependencies — identity resolution + scope/role/tenant guards (§7.1).

`resolve_identity` is a pure function (adapter + headers -> Identity) so it is
unit-testable without FastAPI or a DB. The FastAPI wrappers add HTTP semantics.
"""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request

from ..adapters import AuthError, Identity, get_auth
from ..config import get_settings


def _appkey_lookup(prefix: str) -> dict | None:
    """Real DB lookup for app_key by prefix. Imported lazily (no DB at import)."""
    from .. import db
    from ..repo import system  # noqa: F401

    with db.connect() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT code, org_id, app_key_hash, scopes, origin_allowlist, active
              FROM fbk.system_registry WHERE app_key_prefix = %s
            """,
            (prefix,),
        )
        row = cur.fetchone()
    if not row:
        return None
    return {
        "system": row[0],
        "org_id": str(row[1]) if row[1] else None,
        "app_key_hash": row[2],
        "scopes": row[3],
        "origin_allowlist": row[4],
        "active": row[5],
    }


def resolve_identity(headers: dict[str, str], auth_name: str, *, secret: str = "",
                     lookup=None) -> Identity:
    """Pure: pick adapter, verify headers. Raises AuthError on bad creds."""
    adapter = get_auth(auth_name, secret=secret, lookup=lookup or _appkey_lookup)
    ident = adapter.verify(headers)
    if ident is None:
        # no creds supplied
        if auth_name == "none":
            return Identity(user="anonymous", scopes=["submit", "read"])
        raise AuthError(401, "missing credentials")
    return ident


def get_identity(request: Request) -> Identity:
    s = get_settings()
    try:
        return resolve_identity(dict(request.headers), s.auth, secret=s.fpa_jwt_secret)
    except AuthError as e:
        raise HTTPException(status_code=e.status, detail=e.detail) from None


def require_scope(scope: str):
    def dep(ident: Identity = Depends(get_identity)) -> Identity:
        if scope not in (ident.scopes or []):
            raise HTTPException(status_code=403, detail=f"scope '{scope}' required")
        return ident
    return dep


def require_role(role: str):
    _ORDER = {"viewer": 0, "triager": 1, "admin": 2}

    def dep(ident: Identity = Depends(get_identity)) -> Identity:
        have = _ORDER.get(ident.role or "", -1)
        if have < _ORDER.get(role, 99):
            raise HTTPException(status_code=403, detail=f"role '{role}' required")
        return ident
    return dep


def require_tenant(ident: Identity, system: str) -> None:
    """Reject cross-tenant access: an identity bound to system A cannot touch B."""
    if ident.system is not None and ident.system != system:
        raise HTTPException(status_code=403, detail="cross-tenant access denied")
