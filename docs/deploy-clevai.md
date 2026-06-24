# Deploy — Clevai (dedicated DB on postgres.clevai.vn)

The only supported runtime topology: **one central FeedbackKB API** holding the DB
credentials, with every consumer (widget, other apps, MCP) reaching the data over
HTTP using an `app_key`. **No consumer ever gets a Postgres grant.** That is the whole
point — the API *is* the permission boundary.

```
 widget / app / mcp ──HTTP + X-App-Key──▶  FeedbackKB API  ──pooled conn──▶  postgres.clevai.vn
   (no DB creds)                          (DATABASE_URL, server-side only)     db=fna, schema=fbk
```

## 1. Database

- Cluster: `postgres.clevai.vn:5432`, database `fna`, schema **`fbk`** (8 tables, migration `0000`+`0001`).
- The API pins `search_path=fbk,public` and tags `application_name=feedbackkb` on every
  pooled connection, so the schema is isolated and the DBA can see/limit our footprint.
- Connection pool is bounded (`DB_POOL_MAX`, default 5) so we never race FPA for the
  SUPERUSER-reserved slots on the shared cluster. Keep it small.

> Schema `fbk` lives inside `fna` today (the API user can create/alter tables there).
> If ops later provisions a separate `feedback_kb` database, only `DATABASE_URL` changes —
> no code change.

Apply the schema once (creds from the ops vault, never committed):

```bash
cd packages/server
export DATABASE_URL='postgresql://<db_user>:<db_password>@postgres.clevai.vn:5432/fna'
.venv/Scripts/python -m yoyo apply --batch --database "$DATABASE_URL" ../../migrations
```

## 2. Run the API

```bash
cd packages/server
python -m venv .venv && . .venv/Scripts/activate     # bin/activate on *nix
pip install -e .
cp ../../.env.example .env                            # fill DATABASE_URL from vault
uvicorn feedbackkb_server.app:app --host 0.0.0.0 --port 8000
```

`.env` essentials (real secrets from the vault, not the repo):

| Var | Value |
|-----|-------|
| `DATABASE_URL` | `postgresql://<user>:<pw>@postgres.clevai.vn:5432/fna` |
| `DB_POOL_MAX` | `5` (cap on shared-cluster slots) |
| `FEEDBACKKB_AUTH` | `appkey` (consumers authenticate by key, no DB grant) |
| `FEEDBACKKB_KNOWLEDGE` | `pg` |
| `FEEDBACKKB_STORAGE` | `gcs` (+ `GCS_BUCKET`) |

## 3. Onboard a consumer (zero DB permission)

Admin issues a scoped key; the consuming system only ever sends that key.

```bash
# admin call (admin role) -> returns { app_key } shown ONCE
curl -X POST https://<api-host>/admin/register \
  -H 'Authorization: Bearer <admin_jwt>' \
  -d '{"code":"FPS","name":"Payment System"}'
```

The consumer then calls the API with the key — no Postgres, no DSN, no grant:

```http
POST /api/feedback
X-App-Key: <app_key>
{ "system":"FPS", "message":"<title + body>" }
```

Keys are stored as `sha256` only, scoped, origin-allowlisted, and rotatable
(`POST /admin/systems/{code}/rotate`). See [integration-guide.md](integration-guide.md)
for forward/sync/knowledge-only adoption modes.

## 4. Shutdown

The app drains the pool on shutdown (FastAPI lifespan), releasing slots promptly.
