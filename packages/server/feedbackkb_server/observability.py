"""Observability — Prometheus metrics + /metrics endpoint (§7.7, Step 10).

Counters/gauges/histograms for request latency, upload failures, and agent queue
depth. A dedicated registry keeps test runs isolated (no global-state bleed).
"""

from __future__ import annotations

from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, Counter, Gauge, Histogram, generate_latest

REGISTRY = CollectorRegistry()

REQUEST_LATENCY = Histogram(
    "fbk_request_latency_seconds", "Request latency", ["method", "path"], registry=REGISTRY
)
UPLOAD_FAIL = Counter(
    "fbk_upload_fail_total", "Attachment upload failures", registry=REGISTRY
)
RATE_LIMITED = Counter(
    "fbk_rate_limited_total", "Requests rejected by rate limit", registry=REGISTRY
)
QUEUE_DEPTH = Gauge(
    "fbk_agent_queue_depth", "Queued agent_task rows", registry=REGISTRY
)


def render() -> tuple[bytes, str]:
    return generate_latest(REGISTRY), CONTENT_TYPE_LATEST
