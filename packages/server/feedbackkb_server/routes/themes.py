"""Theme analytics route (ISP Phase 7, Step 47).

GET /api/themes?system=&days=  -> clusters of feedback by meaning over time (viewer+).
Returns [] with a note when embeddings are off (FEEDBACKKB_EMBED=none).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from .. import db
from ..adapters import Identity
from ..config import get_settings
from ..security.deps import require_role
from ..service import themes as themes_svc

router = APIRouter(prefix="/api/themes", tags=["themes"])


@router.get("")
def list_themes(system: str | None = None, days: int = 30,
                ident: Identity = Depends(require_role("viewer"))):
    if get_settings().embed == "none":
        return {"themes": [], "note": "set FEEDBACKKB_EMBED to enable theme clustering"}
    scope_system = ident.system or system
    with db.connect() as conn:
        return {"themes": themes_svc.quantify(conn, system=scope_system, days=days)}
