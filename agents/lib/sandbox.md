# Fixer sandbox (§7.4) — hard constraints for any agent that writes code

- **Isolation:** each fix runs in a fresh `git worktree`; the agent only ever
  commits to a branch named `feedbackkb/fix-*`. NEVER main/prod.
- **Credentials:** a GitHub fine-grained PAT scoped to ONE repo (contents:write +
  pull_request). Never an org-wide or write-all token.
- **Bash allowlist:** only `{pytest, npm test, ruff, build}` run unattended. Any
  other command (`rm -rf`, `curl`, package installs, network) requires explicit
  human approval. A wrapper script enforces this and logs every command to
  `feedback_event` (actor_type=agent, request_id).
- **CI gate:** the human merges only after CI is green on the PR (gate CL5).
- **No prod apply:** applying to prod / merging is irreversible -> always the human.
