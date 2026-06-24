"""ISP Phase 7 (Steps 43/44/46/47/48): embedding fallback, score, clustering, setup guard.

DB-bound semantic paths (44/45) need pgvector + a model and are exercised at deploy;
here we cover the pure cores + the off-by-default safety that keeps P1-P4 working.
"""

from pathlib import Path

from feedbackkb_server.service import embedding, fixability, themes

ROOT = Path(__file__).resolve().parents[3]


# --- Step 43: embedding off-by-default ---

def test_embed_off_returns_none():
    assert embedding.embed(["a", "b"], adapter="none") == [None, None]
    assert embedding.embed_one("x", adapter="none") is None


def test_to_pgvector_format():
    assert embedding.to_pgvector([1.0, 2.5]) == "[1.0,2.5]"


# --- Step 46: fixability score + gate ---

def test_fixability_score_and_gate():
    high = fixability.score(lesson_match=True, grounding=True, dedupe_clear=True, severity_known=True)
    assert high == 1.0 and fixability.is_auto(high, 0.6)
    low = fixability.score(lesson_match=False, grounding=False, dedupe_clear=True, severity_known=True)
    assert low == 0.35 and not fixability.is_auto(low, 0.6)  # no lesson -> wait for human


# --- Step 47: incremental clustering ---

def test_themes_cluster_by_meaning():
    items = [
        ([1.0, 0.0], {"name": "a", "created_at": "1"}),
        ([0.99, 0.01], {"name": "b", "created_at": "2"}),   # ~same dir -> same cluster
        ([0.0, 1.0], {"name": "c", "created_at": "3"}),     # orthogonal -> new cluster
    ]
    clusters = themes.assign(items)
    assert len(clusters) == 2
    summary = themes.summarize(clusters)
    assert summary[0]["count"] == 2  # biggest theme first


# --- Step 48: zero-tech-question setup guard (decision #9) ---

def test_skills_do_not_leak_sql_jargon_to_user():
    banned = ["DROP SCHEMA", "CASCADE", "ivfflat", "vector(", "pg_isready"]
    skills = list((ROOT / ".claude" / "skills").glob("feedbackkb-*/SKILL.md"))
    assert skills, "no feedbackkb skills found"
    for f in skills:
        txt = f.read_text(encoding="utf-8")
        for b in banned:
            assert b not in txt, f"{f.name} leaks tech jargon to user: {b!r}"


def test_env_example_has_all_tech_defaults():
    env = (ROOT / ".env.example").read_text(encoding="utf-8")
    for key in ["DATABASE_URL", "DB_POOL_MAX", "FEEDBACKKB_AUTH", "FEEDBACKKB_EMBED",
                "FIXABILITY_MIN"]:
        assert key in env, f"{key} missing from .env.example (tech default must be code-side)"
