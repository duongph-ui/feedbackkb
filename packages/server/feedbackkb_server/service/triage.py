"""Heuristic triage classifier (§2.1, Step 26).

Deterministic suggestion of type / name / severity from the raw message so the
auto-triage runtime can move feedback off `new` WITHOUT a live LLM. A Claude
Triage agent can override any field later via apply_triage(); this is the V1
floor that keeps the queue draining.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

_BUG = ("loi", "sai", "fail", "error", "crash", "bug", "khong chay", "khong hoat dong",
        "treo", "vo", "exception", "500", "404")
_IDEA = ("de xuat", "nen co", "feature", "y tuong", "cai tien", "mong", "giá như", "gia nhu",
         "wish", "would be nice")
_CRIT = ("crash", "mat du lieu", "khong dung duoc", "data loss", "down", "khong vao duoc")
_HIGH = ("loi", "sai", "fail", "error", "500", "blocker", "chan")


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFD", s.lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


@dataclass
class TriageGuess:
    type: str        # bug | idea | question
    name: str        # short title
    severity: str    # low | med | high | crit


def classify_type(message: str) -> str:
    m = _norm(message)
    if any(w in m for w in _BUG):
        return "bug"
    if any(w in m for w in _IDEA):
        return "idea"
    return "question"


def guess_severity(message: str, ftype: str) -> str:
    m = _norm(message)
    if any(w in m for w in _CRIT):
        return "crit"
    if ftype == "bug" and any(w in m for w in _HIGH):
        return "high"
    if ftype == "bug":
        return "med"
    return "low"


def make_name(message: str, limit: int = 60) -> str:
    first = re.split(r"[\n.!?]", message.strip(), 1)[0].strip()
    first = re.sub(r"\s+", " ", first)
    return (first[: limit - 1] + "…") if len(first) > limit else (first or "feedback")


def triage(message: str) -> TriageGuess:
    ftype = classify_type(message)
    return TriageGuess(type=ftype, name=make_name(message), severity=guess_severity(message, ftype))
