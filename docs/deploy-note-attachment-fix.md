# Deploy Note — FeedbackKB attachment image fix

**Ngày:** 2026-06-29
**PR:** #1 (duongph-ui/feedbackkb, branch master) — đã MERGED
**Mục tiêu:** AI fix-agent + reviewer đọc được ảnh screenshot user đính kèm.

## Vấn đề đang xảy ra trên prod

Server prod (`https://fpa.mikai.tech/feedbackkb`) **chưa chạy code sau PR #1**. Verify live:

| Endpoint | Kết quả | Mong đợi sau deploy |
|---|---|---|
| `GET /api/feedback/attachment/{id}` | 200, trả signed URL ✅ | 200 |
| `GET /local-store/{key}?expires&sig` | **404** ❌ | 200 + bytes ảnh |
| `GET /api/feedback/attachment/{id}/content` | **404** ❌ | 200 + bytes ảnh |

→ Ảnh user submit (vd attachment `cc2f0938`, status=ready, 172KB) **không serve được** → AI review screenshot fail.

## Root cause (đã fix trong code, cần deploy)

1. `LocalStorage` cũ = in-memory dict + `get_storage()` tạo instance mới mỗi request → bytes mất ngay sau upload.
2. Thiếu route serve bytes (`/local-store`, `/content`).

PR #1 đã sửa: disk-backed LocalStorage + `get_storage` singleton (`@lru_cache`) + 2 route serve + MCP tool `get_attachment_image`.

## Việc cần làm (DevOps)

### 1. Redeploy server (BẮT BUỘC)
- Pull `master` mới nhất (sau PR #1).
- Rebuild + restart `packages/server` (FastAPI).

### 2. Cấu hình storage bền (BẮT BUỘC — nếu bỏ qua, restart mất ảnh)

Env hiện tại (`packages/server/.env.run`) **chỉ có** `DATABASE_URL` → storage default = `local`, dir default = tempdir (mất khi restart container).

**Dùng S3 + CDN (đã chọn — env đã set sẵn cho stag/prod):**

Set:
```
FEEDBACKKB_STORAGE=s3
```
S3Storage adapter đọc trực tiếp các env infra có sẵn:
```
AWS_S3_ACCESS_ID          # credentials
AWS_S3_ACCESS_KEY
AWS_S3_BUCKET_NAME        # bucket
AWS_S3_ENDPOINT           # endpoint URL (S3-compatible / region)
AWS_S3_PATH_UPLOADING     # key prefix (folder) cho upload
CDN_HOST_NAME             # nếu set, signed URL = https://{CDN}/{key}
```
- Object key lưu trong DB = full key (`{AWS_S3_PATH_UPLOADING}/{uuid}`) → đọc lại không cần env.
- `get_signed_url`: có `CDN_HOST_NAME` → trả CDN URL public; không có → presigned S3 URL.
- Cần `boto3` trong image server (`pip install boto3`).

> Code: `packages/server/feedbackkb_server/adapters/storage.py` → `S3Storage`. Test: `tests/test_adapters.py::test_s3_uses_clevai_env_prefix_and_cdn`.

(Fallback nếu không dùng cloud: `FEEDBACKKB_STORAGE=local` + `FEEDBACKKB_LOCAL_DIR=/data/feedbackkb-attachments` + mount volume bền.)

### 3. Verify sau deploy
```bash
B=https://fpa.mikai.tech/feedbackkb
# lấy signed url
curl -s -H "X-System: FPA" "$B/api/feedback/attachment/cc2f0938-bc2c-43d1-9a06-492eb7fafef5"
# fetch bytes — phải 200 + image/png
curl -s -o /dev/null -w "%{http_code} %{content_type}\n" \
  -H "X-System: FPA" \
  "$B/api/feedback/attachment/cc2f0938-bc2c-43d1-9a06-492eb7fafef5/content"
```
Kỳ vọng: `200 image/png`.

## Lưu ý

- Ảnh đã submit TRƯỚC khi fix deploy (vd `cc2f0938`, `3ea99a6d`, `2469cc81`): metadata row còn (status=ready) nhưng **bytes đã mất** (in-memory). Sau deploy vẫn 404 với các ảnh cũ này — chỉ ảnh submit MỚI sau deploy mới đọc được.
- MCP server (`packages/mcp`) cũng cần redeploy để có tool `get_attachment_image`.
