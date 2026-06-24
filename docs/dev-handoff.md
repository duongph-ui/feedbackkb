# FeedbackKB — Hướng dẫn cài & chạy (handoff)

> File này an toàn để gửi đi — **không chứa secret**. Cred DB lấy riêng từ vault, không nằm trong repo.

Repo: https://github.com/duongph-ui/feedbackkb

## Mô hình triển khai (đọc trước)

**Một API trung tâm** giữ cred DB; mọi consumer gọi qua HTTP bằng `app_key` và **không bao giờ được cấp quyền Postgres**. API chính là ranh giới quyền. DB là DB riêng của FeedbackKB trên `postgres.clevai.vn:5432` (schema `fbk`).

```
 widget / app / mcp ──HTTP + X-App-Key──▶  FeedbackKB API  ──pool──▶  postgres.clevai.vn (schema fbk)
   (không cred DB)                         (DATABASE_URL, chỉ phía server)
```

Hệ quả: **chỉ 1 máy (server) cần cred DB**. Mọi máy/người khác dùng qua HTTP → không cần cred.

---

## Ai cần gì

| Vai | Cần cred DB? | Làm gì |
|---|---|---|
| Tích hợp app (consumer) | ❌ Không | Gọi API đã deploy + `app_key` (hoặc `auth=none` → không cần gì) |
| Dev verify code | ❌ Không | `pytest` — test đụng DB tự skip |
| Máy chạy API server | ✅ Bắt buộc | Server phải connect Postgres → phải có `DATABASE_URL` |

---

## Yêu cầu

- Python ≥ 3.11 + pip
- (Tùy chọn, chỉ khi build widget/mcp/cli) Node ≥ 20 + pnpm
- **KHÔNG cần Docker.** Không cần Postgres local.
- Nếu chạy server thật: mạng tới `postgres.clevai.vn:5432` + cred DB (xem mục Cred).

---

## Chạy

### 1. Verify code (không cần DB, không cần cred)

```bash
cd packages/server
python -m venv .venv && . .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest                                            # ~82 pass, DB tests tự skip
```

Server lên được mà chưa cần DB — chỉ endpoint đụng Postgres mới cần `DATABASE_URL`:

```bash
uvicorn feedbackkb_server.app:app --port 8000
curl http://localhost:8000/healthz                # {"status":"ok"} — không chạm DB
```

### 2. Chạy đầy đủ (cần cred DB)

```bash
cp ../../.env.example .env
# sửa .env:
#   DATABASE_URL=postgresql://<user>:<pw>@postgres.clevai.vn:5432/fna
uvicorn feedbackkb_server.app:app --port 8000
```

Apply schema 1 lần (nếu schema `fbk` chưa có):

```bash
python -m yoyo apply --batch --database "$DATABASE_URL" ../../migrations
```

---

## Cred DB — lấy ở đâu, cách tránh file vault

Cred KHÔNG nằm trong repo (gitignored). Để chạy server, chọn 1 cách nạp `DATABASE_URL`:

1. **Env injection (khuyên)** — không lưu file, set thẳng biến môi trường:
   ```bash
   export DATABASE_URL='postgresql://<user>:<pw>@postgres.clevai.vn:5432/fna'
   uvicorn feedbackkb_server.app:app --port 8000
   ```
   Cred đặt ở CI secret / k8s secret / systemd EnvironmentFile.

2. **Secret manager** — GCP Secret Manager / HashiCorp Vault; app đọc lúc boot. Code chỉ đọc `DATABASE_URL` từ env nên cắm nguồn nào cũng được, không sửa code.

3. **User DB riêng least-privilege** — nhờ devops cấp user chỉ quyền schema `fbk` (thay vì user prod dùng chung), giảm rủi ro.

> Cred thật (host/user/password) **xin riêng từ người quản trị**, gửi qua kênh an toàn. KHÔNG commit, KHÔNG để trong file gửi chung.

**Không thể bỏ DB hoàn toàn:** mọi route ghi/đọc cần Postgres. Không dùng SQLite thay được (DDL Postgres-specific: tsvector, trigger, `gen_random_uuid`, `FOR UPDATE SKIP LOCKED`).

---

## Cấu hình `.env` chính

| Var | Giá trị | Ghi chú |
|---|---|---|
| `DATABASE_URL` | `postgresql://<user>:<pw>@postgres.clevai.vn:5432/fna` | chỉ phía server |
| `DB_POOL_MAX` | `5` | trần connection trên cụm chung (đừng tranh slot FPA) |
| `FEEDBACKKB_AUTH` | `appkey` \| `none` \| `jwt` | `appkey` = consumer không cần quyền DB |
| `FEEDBACKKB_KNOWLEDGE` | `pg` | |
| `FEEDBACKKB_STORAGE` | `gcs` \| `s3` \| `local` | |

---

## Onboard consumer KHÔNG cần admin cấp gì

Ghép `FEEDBACKKB_AUTH=none` với 1 trong 2:

- **Seed env** (kín, khuyên): ops set 1 lần, startup tự tạo system row:
  ```
  FEEDBACKKB_AUTH=none
  FEEDBACKKB_SEED_SYSTEMS=FPS:Payment System,FPA:Analytics
  ```
- **Open-register** (zero-touch, chỉ mạng nội bộ tin cậy): feedback đầu tiên với system lạ tự tạo row:
  ```
  FEEDBACKKB_AUTH=none
  FEEDBACKKB_OPEN_REGISTER=true     # public-facing thì để false
  ```

Consumer chỉ cần gọi:
```http
POST /api/feedback
{ "system":"FPS", "message":"..." }
```

Hoặc dùng `auth=appkey` + admin cấp key 1 lần:
```bash
curl -X POST https://<api-host>/admin/register \
  -H 'Authorization: Bearer <admin_jwt>' \
  -d '{"code":"FPS","name":"Payment System"}'      # → app_key (hiện 1 lần)
# consumer gửi:  X-App-Key: <app_key>
```

---

## Hỏi nhanh

- **Báo cần Docker?** Bỏ qua — Docker không cần. Chạy bằng `uvicorn` + `DATABASE_URL`.
- **Test có cần DB?** Không — `pytest` tự skip test đụng DB.
- **Máy khác clone không có cred?** Đúng thiết kế. Test thì `pytest`; demo client thì trỏ API đã deploy; tự dựng server thì xin cred riêng.
