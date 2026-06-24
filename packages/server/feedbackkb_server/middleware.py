"""Cross-cutting middleware: request-id correlation + latency metrics (Step 2/10)."""

from __future__ import annotations

import time
import uuid

from fastapi import HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from . import observability as obs
from .service.ratelimit import RateLimiter

REQUEST_ID_HEADER = "X-Request-Id"


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get(REQUEST_ID_HEADER) or uuid.uuid4().hex
        request.state.request_id = rid
        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = rid
        return response


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        obs.REQUEST_LATENCY.labels(request.method, request.url.path).observe(
            time.perf_counter() - start
        )
        return response


# shared limiter; production swaps backend for slowapi+Redis (REDIS_URL).
_LIMITER = RateLimiter(limit=60, window_s=60)


def rate_limit(request: Request) -> None:
    """Dependency: 429 when (ip, system, key) exceeds the window."""
    ip = request.client.host if request.client else "unknown"
    sys = request.headers.get("X-System")
    prefix = (request.headers.get("X-App-Key") or "")[:8] or None
    if not _LIMITER.allow(RateLimiter.key(ip, sys, prefix)):
        obs.RATE_LIMITED.inc()
        raise HTTPException(status_code=429, detail="rate limit exceeded")


__all__ = ["RequestIdMiddleware", "MetricsMiddleware", "rate_limit", "REQUEST_ID_HEADER"]
