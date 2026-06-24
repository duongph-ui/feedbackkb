"""Schema constants for fbk.* — single source for enum values + table names.

Kept in sync with migrations/0001_fbk_core.sql. Services import these instead of
hardcoding string literals, so a status/stage typo fails at import not runtime.
"""

from __future__ import annotations

TABLES = (
    "org",
    "system_registry",
    "feedback",
    "feedback_attachment",
    "feedback_event",
    "agent_task",
    "knowledge_ref",
    "knowledge_doc",
)

# enum domains (mirror CHECK constraints)
FEEDBACK_TYPES = ("bug", "idea", "question")
FEEDBACK_SOURCES = ("widget", "api", "mcp", "forward", "sync")
SEVERITIES = ("low", "med", "high", "crit")
ATTACHMENT_STATUS = ("uploading", "ready", "scanned", "quarantined")
ATTACHMENT_KINDS = ("screenshot", "image")
AGENT_STAGES = ("triage", "analyze", "fix", "knowledge")
AGENT_STATUS = ("queued", "running", "done", "need_human", "failed")
KNOWLEDGE_STATUS = ("draft", "trusted")
ACTOR_TYPES = ("agent", "human", "system")

# feedback status machine (AP §2.4-CL2 / P2)
FEEDBACK_STATUS = (
    "new", "triaged", "needs_info", "in_progress", "blocked",
    "verified", "resolved", "wontfix", "dup", "reopened",
)
