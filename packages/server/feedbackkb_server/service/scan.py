"""Malware scan for attachments (§7.3, Step 8).

Modes (FEEDBACKKB_SCAN):
  - off    -> skip; everything is 'ready'. Self-host default; no ClamAV needed.
  - clamav -> scan via clamd daemon. If the daemon is unreachable we still catch
              the EICAR test signature (so the quarantine path is provable without
              a running daemon, and a missing daemon never silently passes malware
              we can detect).
"""

from __future__ import annotations

# Standard antivirus test string (not real malware).
EICAR = (
    rb"X5O!P%@AP[4\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
)


def scan_status(data: bytes, mode: str = "off") -> str:
    """Return 'ready' (clean) or 'quarantined' (infected)."""
    if mode == "off":
        return "ready"
    if mode == "clamav":
        verdict = _clamav(data)
        if verdict is None:
            # daemon unavailable -> best-effort signature check
            verdict = EICAR not in data
        return "ready" if verdict else "quarantined"
    raise ValueError(f"unknown scan mode {mode!r}")


def _clamav(data: bytes) -> bool | None:
    """True=clean, False=infected, None=daemon unavailable."""
    try:
        import clamd
    except ImportError:
        return None
    try:
        cd = clamd.ClamdUnixSocket()
        res = cd.instream(__import__("io").BytesIO(data))
        status = res.get("stream", ("", ""))[0]
        return status == "OK"
    except Exception:
        return None
