# FeedbackKB

Internal-tooling system that does two things in one place:

1. **Feedback intake** — a 1-field widget (auto-screenshot, paste image) that lands user feedback in Postgres, then an agent team triages it automatically and proposes fixes behind a human approval gate.
2. **Bug-fix knowledge capture** — a `/capture-fix` skill + Stop-hook records the lesson from every real fix into a searchable wiki, so knowledge stops leaking out of one-off Claude prompts.

Open-source (MIT), self-hostable. Standalone-first backend + pluggable adapters (storage / search / auth / knowledge). Clevai/FPA is just one reference instance.

> Design docs live in [`docs/`](docs/): ArchitecturePack (`architecturepack_feedbackkb_*.html`) and the Incremental Step Plan (`IncrementalStepPlan_feedbackkb.md`).

## Repo layout

```
packages/
  server/   # FastAPI standalone — /api/feedback, agent orchestrator
  widget/   # @clevai/feedbackkb-widget (React + vanilla)   [later phase]
  mcp/      # feedbackkb-mcp                                 [later phase]
  cli/      # feedbackkb register|init-mcp|init-hook|sync    [later phase]
adapters/   # storage · search · auth · knowledge (chosen via FEEDBACKKB_* env)
migrations/ # SQL (yoyo) creating schema fbk.*
docs/       # AP + ISP + audit
```

## Quickstart (dev)

```bash
# 1. Python server
cd packages/server
python -m venv .venv && . .venv/Scripts/activate   # Windows; use bin/activate on *nix
pip install -e ".[dev]"
pytest                                              # unit tests

# 2. Full stack (needs Docker) — Postgres + API
cp .env.example .env
docker compose up -d
```

## Status

Phase 0 (project init) — monorepo skeleton, Postgres + migration runner, FastAPI skeleton, adapter interfaces. See `docs/IncrementalStepPlan_feedbackkb.md` for the full 44-step plan.

## License

MIT — see [LICENSE](LICENSE).
