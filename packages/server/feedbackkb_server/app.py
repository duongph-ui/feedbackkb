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


@asynccontextmanager
async def _lifespan(app: FastAPI):
    # Pool is built lazily on first DB use; nothing to warm here. On shutdown we
    # drain it so the dedicated DB's connection slots are released promptly.
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
