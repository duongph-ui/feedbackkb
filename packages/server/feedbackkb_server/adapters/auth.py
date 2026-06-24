"""Auth adapter — resolve request identity (§7.1).

Three identities: anonymous (`none`), app_key (`appkey`, scoped + origin-locked +
tenant-bound), app-host JWT (`jwt`). The adapter is pure: `AppKeyAuth` takes an
injectable `lookup(prefix) -> dict|None` so it never imports the DB layer (the
route wires the real repo lookup; tests inject a fake).
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Callable

from ..security import appkey


@dataclass
class Identity:
    user: str = "anonymous"
    system: str | None = None
    org_id: str | None = None
    scopes: list[str] = field(default_factory=list)
    role: str | None = None


class AuthError(Exception):
    """Credentials present but invalid (-> 401/403). Absence of creds is not an error."""

    def __init__(self, status: int, detail: str):
        self.status = status
        self.detail = detail
        super().__init__(detail)


class AuthAdapter(abc.ABC):
    @abc.abstractmethod
    def verify(self, headers: dict[str, str]) -> Identity | None:
        """Return an Identity, or None when no credentials are supplied."""


def _h(headers: dict[str, str], name: str) -> str | None:
    """Case-insensitive header read."""
    lname = name.lower()
    for k, v in headers.items():
        if k.lower() == lname:
            return v
    return None


class NoneAuth(AuthAdapter):
    def verify(self, headers: dict[str, str]) -> Identity | None:
        return Identity(user="anonymous", scopes=["submit", "read"])


class JwtAuth(AuthAdapter):
    """Verify app-host JWT (HS256). user_email from claim; raises on bad signature."""

    def __init__(self, secret: str):
        self._secret = secret

    def verify(self, headers: dict[str, str]) -> Identity | None:
        auth = _h(headers, "Authorization")
        if not auth or not auth.startswith("Bearer "):
            return None
        import jwt

        token = auth[len("Bearer "):]
        try:
            claims = jwt.decode(token, self._secret, algorithms=["HS256"])
        except jwt.PyJWTError as e:
            raise AuthError(401, f"invalid jwt: {e}") from None
        return Identity(
            user=claims.get("email") or claims.get("sub") or "user",
            system=claims.get("system"),
            org_id=claims.get("org_id"),
            scopes=claims.get("scopes", ["submit", "read"]),
            role=claims.get("role", "viewer"),
        )


class AppKeyAuth(AuthAdapter):
    """Verify X-App-Key against system_registry hash; enforce origin allowlist + tenant."""

    def __init__(self, lookup: Callable[[str], dict | None]):
        # lookup(prefix) -> {app_key_hash, scopes, origin_allowlist, system, org_id, active}
        self._lookup = lookup

    def verify(self, headers: dict[str, str]) -> Identity | None:
        raw = _h(headers, "X-App-Key")
        if not raw:
            return None
        row = self._lookup(appkey.display_prefix(raw))
        if not row or not row.get("active", True):
            raise AuthError(401, "unknown or inactive app_key")
        if not appkey.verify(raw, row["app_key_hash"]):
            raise AuthError(401, "invalid app_key")
        allow = row.get("origin_allowlist")
        if allow:
            origin = _h(headers, "Origin") or _h(headers, "Referer") or ""
            if not _origin_allowed(origin, allow):
                raise AuthError(403, "origin not allowed")
        return Identity(
            user="anonymous",
            system=row.get("system"),
            org_id=row.get("org_id"),
            scopes=list(row.get("scopes") or []),
            role=None,
        )


def _origin_allowed(origin: str, allowlist: str) -> bool:
    allowed = {a.strip() for a in allowlist.split(",") if a.strip()}
    return any(a in origin for a in allowed)
