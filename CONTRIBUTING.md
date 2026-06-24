# Contributing to FeedbackKB

Thanks for helping. FeedbackKB is MIT-licensed and self-hostable; keep everything
generic (no Clevai-specific hardcoding — use config/adapters).

## Dev setup
```bash
# Python server
cd packages/server
python -m venv .venv && . .venv/Scripts/activate   # bin/activate on *nix
pip install -e ".[dev]"
pytest && ruff check .

# Node packages (widget / mcp / cli)
pnpm install
pnpm -r test
pnpm -r lint
```

## Ground rules
- **No secrets in the repo.** Only `.env.example`. CI runs a secret scan; a hit
  blocks the merge (§6.5).
- **Parameterised SQL only** — never f-string user values into a query.
- **Least privilege** for agents — Triage/Analyst have no Edit/Bash.
- **Adapters over hardcoding** — storage/search/auth/knowledge are pluggable; add
  a new backend as an adapter, don't special-case it in a service.
- **Tests required.** Each change ships unit tests; DB-bound tests self-skip when
  `DATABASE_URL` is unset.

## Security
Report vulnerabilities privately (see SECURITY.md). Do not open a public issue for
a live vulnerability.
