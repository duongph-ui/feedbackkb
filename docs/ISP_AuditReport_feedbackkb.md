# ISP Audit Report — FeedbackKB

> **Role:** QA · **Ngày:** 2026-06-24
> **ISP:** `IncrementalStepPlan_feedbackkb.md` (42 step / 7 phase)
> **AP (truth source):** `architecturepack_feedbackkb_V1.0_2026-06-24.html` (V1.4)
> **Tiêu chí:** ①Data ②API ③UI ④Logic ⑤AC ⑥Lib ⑦Deps · Verdict PASS/ENRICH/BLOCK

## 1. Audit Summary

| Verdict | Count | Steps |
|---|---|---|
| **PASS** | 33 | 0,2,3,5,9,11,12,13,14,15,16,17,18,19,20,22,23,24,25,26,27,28,29,30,31,33,34,35,36,38,39,40,41 |
| **ENRICH** | 9 | 1,4,6,7,8,10,21,32,37 |
| **BLOCK** | 0 | — |
| **Tổng** | 42 | |

> **Kết luận:** ISP chất lượng cao, build-ready. **0 BLOCK** — không bí spec cần redesign. 9 ENRICH = pin thư viện/công cụ cụ thể AP chưa chốt (AI cần để khỏi tự bịa). 6 Open Question (§6) = xác nhận deploy-time/devops, KHÔNG chặn thiết kế (đã ghi §8 AP).

## 2. Coverage Matrix (AP → ISP)

| AP section | Mục | ISP step | % |
|---|---|---|---|
| §1 ERD (8 entity) | org/system_registry/feedback/attachment/event/agent_task/knowledge_ref/knowledge_doc | 4 (DDL) + 5,8,9,22,28 (repo) | 100% |
| §2.1 P1–P4 | intake/status/capture/agent pipeline | 11 / 13 / 24 / 26,28,31,32,35 | 100% |
| §2.2 UF1–3 | gửi/capture-fix/fix-gate | 11,17 / 24 / 32,35 | 100% |
| §2.3 W1/W1b/W2 | widget/annotate/dashboard | 14,15,17 / 16 / 19 | 100% |
| §2.4 CL1–CL9 | autonomy/guard/lesson/dedupe/approval/screenshot/enforce/impact/grounding | 26/13/24/25/35/15-17/24,29/34/30 | 100% |
| §3.1 F-01..F-20 | feature→layer | 14-18/11/1,4/13/24/26,28,31,32/26/32,35/19/26-32/21/18,21/15,16/24,29/21/38,39/6-10/31,34,30 | 100% |
| §3.2 A/B/C | classification | 4 (Type B POSUP) + 33 (động) | 100% |
| §3.3 Agent | conductor/triage/analyst/fixer/KW | 28/26/31,34/32/23 | 100% |
| §3.4 MCP | feedbackkb-mcp + 3 cách tích hợp | 21 (+18 widget, 11 REST) | 100% |
| §3.5 Dev workflow | setup/tự-động/data I/O/B1-B4 | 21,24 / 36 | 100% |
| §6 OSS | adapter/self-host/checklist | 3,7,22,37 / 38 / 39 | 100% |
| §7 Security | auth/tenant/privacy/attachment/sandbox/injection/audit/observability | 6/6,12/15,20/8/32/26,30/9/10,40 | 100% |

**Coverage tổng: 100%** — không feature/entity/CL/screen nào rớt. Vượt ngưỡng 95%.

## 3. Audit Table (7 tiêu chí / step)

> UI = "—" cho step thuần BE (không phạt). Lib = "—" khi không export/generate/SDK đặc thù.

| Step | Tên | ①Data | ②API | ③UI | ④Logic | ⑤AC | ⑥Lib | ⑦Deps | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| 0 | Monorepo skeleton | — | — | — | ✅ | ✅ | ✅ | ✅ | PASS |
| 1 | docker+PG+migration runner | ✅ | — | — | ✅ | ✅ | ⚠️ | ✅ | **ENRICH** |
| 2 | FastAPI skeleton+config | — | ✅ | — | ✅ | ✅ | ✅ | ✅ | PASS |
| 3 | Adapter interfaces | — | — | — | ✅ | ✅ | — | ✅ | PASS |
| 4 | Migration fbk.* (8 entity) | ✅ | — | — | ✅ | ✅ | ⚠️ | ✅ | **ENRICH** |
| 5 | system_registry+app_key hash | ✅ | — | — | ✅ | ✅ | ✅ | ✅ | PASS |
| 6 | Auth appkey+jwt+scope | ✅ | ✅ | — | ✅ | ✅ | ⚠️ | ✅ | **ENRICH** |
| 7 | Storage adapter+signed URL | — | ✅ | — | ✅ | ✅ | ⚠️ | ✅ | **ENRICH** |
| 8 | Attachment service+scan | ✅ | ✅ | — | ✅ | ✅ | ❌ | ✅ | **ENRICH** |
| 9 | Audit append-only | ✅ | — | — | ✅ | ✅ | — | ✅ | PASS |
| 10 | Rate-limit+anti-abuse | — | ✅ | — | ✅ | ✅ | ❌ | ✅ | **ENRICH** |
| 11 | POST /api/feedback | ✅ | ✅ | — | ✅ | ✅ | ✅ | ✅ | PASS |
| 12 | GET list+detail | ✅ | ✅ | — | ✅ | ✅ | — | ✅ | PASS |
| 13 | Status machine+PATCH | ✅ | ✅ | — | ✅ | ✅ | — | ✅ | PASS |
| 14 | Widget skeleton 1-ô | — | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | PASS |
| 15 | Auto-screenshot local | — | — | ✅ | ✅ | ✅ | ✅ | ✅ | PASS |
| 16 | Annotate+paste | — | — | ✅ | ✅ | ✅ | ✅ | ✅ | PASS |
| 17 | Widget submit wire API | — | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | PASS |
| 18 | Widget package+CDN | — | — | ✅ | ✅ | ✅ | ✅ | ✅ | PASS |
| 19 | Dashboard read | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | PASS |
| 20 | Privacy config+consent | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ | PASS |
| 21 | MCP+CLI | — | ✅ | — | ✅ | ✅ | ⚠️ | ✅ | **ENRICH** |
| 22 | KnowledgeStore sepo+pg | ✅ | — | — | ✅ | ✅ | ✅ | ✅ | PASS |
| 23 | KW dedupe+trust | ✅ | — | — | ✅ | ✅ | ✅ | ✅ | PASS |
| 24 | capture-fix+hook | ✅ | — | — | ✅ | ✅ | — | ✅ | PASS |
| 25 | Dedupe 2 tầng | ✅ | — | — | ✅ | ✅ | ✅ | ✅ | PASS |
| 26 | Triage agent | ✅ | — | — | ✅ | ✅ | ✅ | ✅ | PASS |
| 27 | link_knowledge | ✅ | — | — | ✅ | ✅ | — | ✅ | PASS |
| 28 | Conductor+queue | ✅ | — | — | ✅ | ✅ | ✅ | ✅ | PASS |
| 29 | Capture metric | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ | PASS |
| 30 | CL9 grounding | ✅ | — | — | ✅ | ✅ | ✅ | ✅ | PASS |
| 31 | Analyst root cause | ✅ | — | — | ✅ | ✅ | ✅ | ✅ | PASS |
| 32 | Fixer sandbox | — | — | — | ✅ | ✅ | ⚠️ | ✅ | **ENRICH** |
| 33 | Classify động A/B/C | ✅ | — | — | ✅ | ✅ | — | ✅ | PASS |
| 34 | Analyst impact+CI | ✅ | — | — | ✅ | ✅ | ✅ | ✅ | PASS |
| 35 | Approval gate+apply | ✅ | — | — | ✅ | ✅ | — | ✅ | PASS |
| 36 | Forward+sync B1/B2 | ✅ | ✅ | — | ✅ | ✅ | ✅ | ✅ | PASS |
| 37 | Search adapter pgvector | ✅ | — | — | ✅ | ✅ | ❌ | ✅ | **ENRICH** |
| 38 | docker full self-host | — | ✅ | — | ✅ | ✅ | ✅ | ✅ | PASS |
| 39 | OSS checklist | — | — | — | ✅ | ✅ | ✅ | ✅ | PASS |
| 40 | Instances+observability | ✅ | — | — | ✅ | ✅ | ✅ | ✅ | PASS |
| 41 | E2E integration | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ | PASS |

## 4. Detailed Findings — ENRICH (9 step)

> Mỗi ENRICH = thiếu **pin thư viện/công cụ** cụ thể. AP cho cơ chế nhưng chưa chốt lib → AI dễ tự bịa. Bổ sung khuyến nghị (default hợp lý, đổi được).

**Step 1 — migration runner (⑥Lib ⚠️):**
- Thiếu: ISP ghi "alembic HOẶC raw SQL apply".
- ENRICH: chốt **raw SQL versioned + `yoyo-migrations`** (nhẹ, không ORM, hợp OSS self-host chạy `*.sql` thuần) HOẶC `alembic` nếu dùng SQLAlchemy models. → Đề xuất **yoyo-migrations** (migrations/ là SQL thuần đúng §6.2). Test thêm: `apply` + `rollback` idempotent.

**Step 4 — FTS tiếng Việt (⑥Lib ⚠️):**
- Thiếu: `search_tsv` GIN nhưng AP/ISP chưa chốt config FTS cho tiếng Việt (Postgres mặc định `simple`/`english` không bỏ dấu).
- ENRICH: dùng `to_tsvector('simple', unaccent(message))` + extension **`unaccent`** (bỏ dấu) để near-dup tiếng Việt chạy đúng. Migration `0001` thêm `CREATE EXTENSION unaccent`. Test thêm: "lỗi" ~ "loi" cùng match.

**Step 6 — JWT lib (⑥Lib ⚠️):**
- ENRICH: **`PyJWT`** verify `FPA_JWT_SECRET` (HS256). Origin allowlist check qua header `Origin`/`Referer`. RBAC role enum trong `system_registry`/JWT claims.

**Step 7 — Storage SDK (⑥Lib ⚠️):**
- ENRICH: adapter `gcs` → **`google-cloud-storage`** (signed URL V4); `s3` → **`boto3`** (presigned URL); `local` → ký HMAC token tự sinh + serve qua endpoint. TTL signed URL default **300s**.

**Step 8 — Malware scan (⑥Lib ❌):**
- Thiếu: AP nói "malware scan" nhưng chưa chốt công cụ.
- ENRICH: **ClamAV** (`clamd` daemon, async scan) → pass=`scanned→ready`, fail=`quarantined`. Self-host: scan optional qua ENV `FEEDBACKKB_SCAN=clamav|off` (máy trắng không bắt buộc ClamAV). Test thêm: EICAR test file → `quarantined`.

**Step 10 — Rate-limit + captcha (⑥Lib ❌):**
- Thiếu: chưa chốt lib rate-limit + captcha provider.
- ENRICH: rate-limit **`slowapi`** (Redis backend, key=IP+system+app_key); captcha anonymous **Cloudflare Turnstile** (verify server-side), config qua ENV (`FEEDBACKKB_CAPTCHA=turnstile|off`). Metrics qua **`prometheus-client`**.

**Step 21 — MCP SDK (⑥Lib ⚠️):**
- ENRICH: **`@modelcontextprotocol/sdk`** (TypeScript) cho `feedbackkb-mcp`; CLI **`commander`** + ghi `.mcp.json`/`.claude/settings.json` qua `jsonc-parser` (giữ comment).

**Step 32 — Fixer sandbox cơ chế (⑥Lib ⚠️):**
- Thiếu: §7.4 yêu cầu "sandbox/worktree cô lập" nhưng chưa chốt cơ chế.
- ENRICH: dùng **`git worktree`** cho mỗi fix (nhánh `feedbackkb/fix-*` cô lập); repo-scoped token = **GitHub fine-grained PAT** (1 repo, contents:write+PR). Bash allowlist enforce qua agent `tools` + wrapper script chặn lệnh ngoài `{pytest,npm test,ruff,build}`. CI = `.github/workflows/fix-ci.yml` (Step 34). Test thêm: lệnh `rm -rf` → blocked.

**Step 37 — pgvector embedding (⑥Lib ❌, P4 deferred):**
- Thiếu: pgvector cần model embedding + dimension, AP §5 #2 hoãn pgvector sau P1.
- ENRICH: khuyến nghị **`pgvector` ext + embedding qua model nhỏ self-host** (`all-MiniLM-L6-v2`, 384-dim) HOẶC OpenAI `text-embedding-3-small` (1536-dim) tuỳ ENV. **Chốt model lúc P4** (Open Q6) — không chặn vì P1 dùng `sepo`/`keyword` adapter. Test: keyword adapter chạy không cần embedding.

## 5. Enriched — bổ sung vào ISP (tóm)

> Áp 9 ENRICH trên = thêm 1 dòng "**Lib:**" vào Components/Scope mỗi step + 1 test case như ghi chú §4. Không đổi Goal/Deps/cấu trúc. Sau khi áp → cả 42 step PASS.

| Step | Thêm vào ISP |
|---|---|
| 1 | Lib: `yoyo-migrations`; test rollback idempotent |
| 4 | `CREATE EXTENSION unaccent`; `to_tsvector('simple',unaccent(...))`; test bỏ-dấu match |
| 6 | Lib: `PyJWT` HS256 |
| 7 | Lib: `google-cloud-storage`/`boto3`; signed TTL 300s |
| 8 | Lib: `ClamAV/clamd`, ENV `FEEDBACKKB_SCAN`; test EICAR |
| 10 | Lib: `slowapi`+Redis, Turnstile, `prometheus-client` |
| 21 | Lib: `@modelcontextprotocol/sdk`,`commander`,`jsonc-parser` |
| 32 | `git worktree` + fine-grained PAT + Bash wrapper allowlist; test block `rm -rf` |
| 37 | pgvector ext + embedding model (chốt P4); P1 dùng keyword/sepo |

## 6. Open Questions (non-blocking — xác nhận deploy-time)

> KHÔNG chặn thiết kế/build. Đã ghi §8 AP. Cần PO/devops chốt trước khi dựng P0/deploy:

1. **PG slot + creds** (Step 1/40): devops cấp slot cluster FPS cho DB `feedback_kb` + creds → vault. *(§8 AP)*
2. **GCS bucket write** (Step 7/40): quyền ghi bucket FPA cho storage adapter `gcs`. *(§8 AP)*
3. **Retention default** (Step 8/20): xác nhận `feedback_attachment.expires_at` = **90 ngày**? *(§8 AP, đề xuất)*
4. **Malware scanner** (Step 8): chấp nhận **ClamAV** + cho self-host tắt qua ENV?
5. **Captcha provider** (Step 10): **Cloudflare Turnstile** cho anonymous submit OK?
6. **pgvector model** (Step 37, P4): chốt lúc P4 — self-host MiniLM-384 hay OpenAI-1536?

## 7. Sign-off

- **ISP Quality Auditor:** ✅ 33 PASS / 9 ENRICH / 0 BLOCK · coverage 100% · DAG no-cycle · mỗi step có BE+FE AC (test cases) + Exit + Deps.
- **Software Architect:** ✅ Phân tầng khớp AP V1.4 (Type B POSUP @ Step 4, Fixer-apply gate động Step 33/35). Security §7 phủ đủ trong P0-P1. OSS adapter standalone-first.
- **Verdict tổng:** **APPROVED có điều kiện** — áp 9 ENRICH (§5, thêm Lib+test, ~30 phút) → build-ready 100%. 6 Open Q xác nhận khi deploy, không chặn code Phase 0-3.

---

**END — ISP Audit Report FeedbackKB** · Next: áp ENRICH → **RunBuildStep (T310-001)** từ Phase 0, hoặc PO chốt 6 Open Q.
