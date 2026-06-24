# Security policy

## Reporting
Report vulnerabilities privately to the maintainers (security@ contact in the repo
settings). Do not open a public issue for a live vulnerability.

## Built-in protections (see AP §7)
- Multi-tenant row-level isolation (`org` / `system`); cross-tenant reads denied.
- app_key stored as `sha256` hash only (never raw); scoped + origin-allowlisted; rotatable.
- Attachments private; signed-URL reads; MIME/size validation; malware scan (ClamAV).
- Auto-screenshot is local-only until send; DOM-mask + route denylist + preview + consent.
- Secret scanning on feedback + lessons before persistence.
- Agent sandbox: branch-only, allowlisted Bash, repo-scoped token, CI gate.
- Prompt-injection defense: untrusted input wrapped as data; trust order code > AP > CLAUDE.md > lesson.
- Append-only audit (`feedback_event`); GDPR export/delete/erase.
