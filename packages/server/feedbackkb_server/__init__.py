"""FeedbackKB server package.

Standalone-first FastAPI backend for feedback intake + agent orchestration.
Clevai integrations (sepo-mcp, GCS, JWT) sit behind adapter interfaces so the
public build has zero Clevai dependency.
"""

__version__ = "0.0.0"
