"""Theme quantification (ISP Phase 7, Step 47, AP P5 — like Enterpret/Unwrap).

Incremental online clustering of feedback embeddings: assign each item to the
nearest existing theme centroid (cosine >= THRESHOLD) else open a new theme; the
centroid is a running mean. No offline kmeans, no fixed taxonomy. The clustering
core is pure (testable without a DB); `quantify` wraps it over a DB window.
"""

from __future__ import annotations

import math

import psycopg

THRESHOLD = 0.8


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def assign(items: list[tuple[list[float], dict]], threshold: float = THRESHOLD) -> list[dict]:
    """items = [(vector, meta)]. Returns clusters: {centroid, count, members[meta]}."""
    clusters: list[dict] = []
    for vec, meta in items:
        best, best_sim = None, -1.0
        for c in clusters:
            s = _cosine(vec, c["centroid"])
            if s > best_sim:
                best_sim, best = s, c
        if best is not None and best_sim >= threshold:
            n = best["count"]
            best["centroid"] = [(best["centroid"][i] * n + vec[i]) / (n + 1)
                                for i in range(len(vec))]
            best["count"] += 1
            best["members"].append(meta)
        else:
            clusters.append({"centroid": list(vec), "count": 1, "members": [meta]})
    return clusters


def summarize(clusters: list[dict]) -> list[dict]:
    out = []
    for c in clusters:
        members = c["members"]
        sev = {}
        for m in members:
            sev[m.get("severity")] = sev.get(m.get("severity"), 0) + 1
        label = max(members, key=lambda m: m.get("created_at") or "").get("name") or "theme"
        out.append({
            "label": label, "count": c["count"], "severities": sev,
            "last_seen": max((m.get("created_at") for m in members), default=None),
        })
    return sorted(out, key=lambda t: t["count"], reverse=True)


def quantify(conn: psycopg.Connection, *, system: str | None, days: int = 30) -> list[dict]:
    """Cluster feedback with embeddings in the window. Empty when embeddings are off."""
    clauses = ["embedding IS NOT NULL", "created_at > now() - (%s || ' days')::interval"]
    params: list = [str(days)]
    if system:
        clauses.append("system = %s")
        params.append(system)
    where = " AND ".join(clauses)
    with conn.cursor() as cur:
        cur.execute(
            f"SELECT id, name, severity, created_at, embedding::text FROM fbk.feedback "
            f"WHERE {where} ORDER BY created_at",
            params,
        )
        rows = cur.fetchall()
    items = []
    for fid, name, severity, created_at, emb in rows:
        vec = [float(x) for x in emb.strip("[]").split(",")] if emb else None
        if vec:
            items.append((vec, {"id": str(fid), "name": name, "severity": severity,
                                "created_at": created_at.isoformat() if created_at else None}))
    return summarize(assign(items))
