"""Feedback status machine (AP §2.4-CL2 / P2, Step 13).

Pure transition table + guard helpers (no DB), so the legal-move logic and the
ensure-lesson rule are unit-testable on their own.
"""

from __future__ import annotations

# allowed transitions: state -> set(next states)
TRANSITIONS: dict[str, set[str]] = {
    "new": {"triaged", "dup"},
    "triaged": {"needs_info", "in_progress", "wontfix"},
    "needs_info": {"triaged"},
    "in_progress": {"blocked", "verified", "wontfix"},
    "blocked": {"in_progress"},
    "verified": {"resolved"},
    "resolved": {"reopened"},
    "reopened": {"in_progress"},
    "wontfix": set(),
    "dup": set(),
}


def is_allowed(old: str, new: str) -> bool:
    return new in TRANSITIONS.get(old, set())


def requires_lesson(type_: str | None, severity: str | None, new_status: str) -> bool:
    """CL2: only a real bug (sev >= med) resolving must carry a knowledge_ref.
    idea/question/trivial skip with a skip_reason."""
    if new_status != "resolved":
        return False
    if type_ != "bug":
        return False
    return severity in ("med", "high", "crit")


class TransitionError(Exception):
    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(detail)
