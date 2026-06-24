"""Approval gate (CL5, Step 35).

Decides what happens after the Analyst verdict + human decision. The agent NEVER
auto-applies to prod (even crit). On approve: lesson draft->trusted + resolve. On
reject: wontfix. Decision logic is pure; the DB writes live in feedback_service /
knowledge repo.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class GateInput:
    verdict: str            # safe | risky | block
    classification: str     # A | B | C
    human_decision: str | None = None  # approve | reject | None (not yet asked)


@dataclass
class GateOutcome:
    reaches_human: bool
    action: str             # await_human | apply | wontfix | return_to_fixer
    lesson_trust: str | None = None  # set to 'trusted' on apply
    new_status: str | None = None


def evaluate(g: GateInput) -> GateOutcome:
    # block never reaches the human — loop back to the Fixer
    if g.verdict == "block":
        return GateOutcome(reaches_human=False, action="return_to_fixer")

    # safe/risky reach the human gate
    if g.human_decision is None:
        return GateOutcome(reaches_human=True, action="await_human")

    if g.human_decision == "approve":
        return GateOutcome(
            reaches_human=True, action="apply",
            lesson_trust="trusted", new_status="resolved",
        )
    return GateOutcome(reaches_human=True, action="wontfix", new_status="wontfix")
