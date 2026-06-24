"""Secret scanning for untrusted input + lessons (§7.5, Step 11/23).

Redacts obvious credentials pasted into feedback/lessons so they never surface
in the dashboard or an agent prompt. Pattern-based (cheap, deterministic);
detect-secrets can be layered in later for entropy detection.
"""

from __future__ import annotations

import re

_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9]{16,}"),                       # OpenAI-style
    re.compile(r"fbk_live_[A-Za-z0-9_\-]{16,}"),              # our own app_key
    re.compile(r"AKIA[0-9A-Z]{16}"),                          # AWS access key
    re.compile(r"ghp_[A-Za-z0-9]{30,}"),                      # GitHub PAT
    re.compile(r"eyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+"),  # JWT
    re.compile(r"(?i)(password|passwd|secret|token)\s*[:=]\s*\S+"),       # key=value
]

REDACTION = "[REDACTED]"


def scan(text: str) -> tuple[str, bool]:
    """Return (redacted_text, has_secret)."""
    found = False
    out = text
    for pat in _PATTERNS:
        out, n = pat.subn(REDACTION, out)
        found = found or n > 0
    return out, found
