"""Auto-triage worker entrypoint (Gap 1 runtime).

    python -m feedbackkb_server.worker          # loop, drain every WORKER_INTERVAL s
    WORKER_ONCE=1 python -m feedbackkb_server.worker   # drain once and exit (cron/CI)

Reaps dead leases, then drains the triage queue via the orchestrator. This is the
deterministic half of the agent team; richer stages park as need_human.
"""

from __future__ import annotations

import os
import time

from . import db
from .service import orchestrator, queue


def tick() -> int:
    with db.connect() as conn:
        queue.reap_expired(conn)
        return orchestrator.drain(conn)


def main() -> None:
    once = bool(os.environ.get("WORKER_ONCE"))
    interval = float(os.environ.get("WORKER_INTERVAL", "2"))
    while True:
        n = tick()
        if n:
            print(f"[worker] processed {n} task(s)", flush=True)
        if once:
            break
        time.sleep(interval)


if __name__ == "__main__":
    main()
