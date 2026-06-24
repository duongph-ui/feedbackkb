"""FastAPI app factory.

`/healthz` is dependency-free (no DB hit) so liveness probes stay green even if
Postgres is briefly down. Business routes mount in later phases.
"""

from __future__ import annotations

from fastapi import FastAPI, Response

from . import observability as obs
from .middleware import MetricsMiddleware, RequestIdMiddleware


def create_app() -> FastAPI:
    app = FastAPI(title="FeedbackKB", version="0.0.0")
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
