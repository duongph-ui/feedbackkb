# Integration guide — adopting FeedbackKB (§3.5.4)

Four ways for an existing system to adopt FeedbackKB. Pick by how much you want
to integrate. B1/B3 are the common picks.

## A. Greenfield (no feedback yet) — 4 commands
```bash
npx feedbackkb register --system FPS --name "Payment System"   # -> app_key
npm i @clevai/feedbackkb-widget        # mount <FeedbackWidget system="FPS"/>
npx feedbackkb init-mcp --key <app_key>
npx feedbackkb init-hook
```

## B1 — Forward (webhook), realtime, minimal change (recommended)
After you save feedback in your own DB, fire one extra call:
```http
POST /api/feedback
X-App-Key: <app_key>
{ "system":"FPS", "message":"<title + body merged>",
  "source":"forward", "external_system":"your-app", "external_id":"<your row id>" }
```
`UNIQUE(system, external_system, external_id)` makes repeated forwards idempotent.
Your UI + DB stay untouched; you gain agent triage + knowledge.

## B2 — Batch sync (no app code change)
```bash
npx feedbackkb sync   # reads your view/export, bulk-forwards with external_id
```
Re-running never duplicates (same idempotency key).

## B3 — Knowledge only (feedback already fine)
Skip intake. Install MCP + `/capture-fix` + the Stop-hook. Your feedback stays
100% yours; you only use FeedbackKB to accumulate + search bug-fix knowledge
(pain #1). This is the lightest adoption.

## B4 — Replace
Drop your old widget, mount `@clevai/feedbackkb-widget` instead. Choose this only
when the old feedback flow is weak.

## Field mapping (B1/B2)
Map your schema to the minimum: `{ system, message (title+body merged),
attachment_ids?, external_system, external_id }`. Extra fields go into `context`.
Triage derives `type` / `name` / `severity`.
