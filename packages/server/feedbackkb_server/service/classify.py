"""Dynamic A/B/C classification of a Fixer patch on a target system (§3.2.2, Step 33).

Pure decision from what the patch touches, per SEPO layerevent rules:
  A = UI/API only (no schema)         -> human merge only
  B = schema, no Layer Event/CalcKR   -> POSUP (target system)
  C = Layer Event/EventDetails OR CalculateKR/ExtractEvent -> POSUP + ARCH
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PatchTouches:
    schema_change: bool = False
    layer_event_rw: bool = False        # reads/writes Layer Event / EventDetails
    calculatekr_write: bool = False     # writes CalculateKR / ExtractEvent
    layer_tables: tuple[str, ...] = ()


def classify(t: PatchTouches) -> str:
    if t.layer_event_rw or t.calculatekr_write:
        return "C"
    if t.schema_change:
        return "B"
    return "A"


def approval_for(klass: str) -> str:
    return {
        "A": "human-merge",
        "B": "POSUP",
        "C": "POSUP+ARCH",
    }[klass]


def result_payload(target_system: str, t: PatchTouches) -> dict:
    klass = classify(t)
    return {
        "target_system": target_system,
        "classification": klass,
        "approval_needed": approval_for(klass),
        "layer_tables_touched": list(t.layer_tables),
    }
