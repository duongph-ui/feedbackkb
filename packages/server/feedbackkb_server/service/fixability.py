"""Fixability / confidence score (ISP Phase 7, Step 46, AP P5 — inspired by Sentry Seer).

Pure scoring of how confidently the pipeline can proceed on a feedback WITHOUT a human.
The orchestrator uses it as a gate: score >= FIXABILITY_MIN -> auto-advance to analyze;
below -> leave for a human to decide. It NEVER gates the apply-to-prod step — that gate
(§3.3) stays human-only regardless of score.
"""

from __future__ import annotations

WEIGHTS = {
    "lesson_match": 0.4,    # a trusted lesson already covers this symptom
    "grounding": 0.25,      # enough context to reason about it
    "dedupe_clear": 0.2,    # dedupe ran and it's a distinct issue
    "severity_known": 0.15,  # severity was determined
}


def score(*, lesson_match: bool, grounding: bool, dedupe_clear: bool,
          severity_known: bool) -> float:
    flags = {
        "lesson_match": lesson_match, "grounding": grounding,
        "dedupe_clear": dedupe_clear, "severity_known": severity_known,
    }
    return round(sum(w for k, w in WEIGHTS.items() if flags[k]), 3)


def is_auto(score_value: float, threshold: float) -> bool:
    return score_value >= threshold
