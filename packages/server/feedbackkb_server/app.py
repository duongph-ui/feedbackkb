"""FastAPI app factory.

`/healthz` is dependency-free (no DB hit) so liveness probes stay green even if
Postgres is briefly down. Business routes mount in later phases.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Response

from . import db
from . import observability as obs
from .middleware import MetricsMiddleware, RequestIdMiddleware


def _seed_systems() -> None:
    """Upsert systems listed in FEEDBACKKB_SEED_SYSTEMS so they accept feedback
    without an admin `register` call. Read straight from env (not Settings) so a
    no-seed test build never touches the DB or needs DATABASE_URL."""
    import os

    raw = os.environ.get("FEEDBACKKB_SEED_SYSTEMS", "").strip()
    if not raw:
        return
    pairs = []
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        code, _, name = item.partition(":")
        code = code.strip()
        if code:
            pairs.append((code, name.strip() or code))
    if not pairs:
        return
    from .repo import system as sysrepo

    with db.connect() as conn:
        for code, name in pairs:
            sysrepo.seed_system(conn, code, name)


@asynccontextmanager
async def _lifespan(app: FastAPI):
    # Pool is built lazily on first DB use; nothing to warm here. Seed configured
    # systems on startup. On shutdown drain the pool so the dedicated DB's
    # connection slots are released promptly.
    _seed_systems()
    yield
    db.close_pool()


def create_app() -> FastAPI:
    app = FastAPI(title="FeedbackKB", version="0.0.0", lifespan=_lifespan)
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(MetricsMiddleware)

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/metrics")
    def metrics() -> Response:
        body, content_type = obs.render()
        return Response(content=body, media_type=content_type)

    from .routes import admin, attachment, config, feedback

    app.include_router(admin.router)
    app.include_router(attachment.router)
    app.include_router(feedback.router)
    app.include_router(config.router)
    return app


app = create_app()
