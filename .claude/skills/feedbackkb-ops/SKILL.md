---
name: feedbackkb-ops
description: Luồng vận hành/admin FeedbackKB — xoay app_key, GDPR export/delete/erase, config privacy/retention, batch sync feedback cũ. Việc quản trị định kỳ trên DB trung tâm, qua admin route (cần role admin).
---

# /feedbackkb-ops

Các tác vụ vận hành định kỳ. Cần **role admin** (JWT admin). Không phải việc hằng ngày.

## Tác vụ (chọn theo nhu cầu)
1. **Rotate app_key** (lộ key / định kỳ):
   ```
   POST /admin/systems/<CODE>/rotate   → app_key mới (hiện 1 lần)
   ```
   Key cũ vô hiệu ngay (lưu hash, không lưu raw).
2. **GDPR** (yêu cầu người dùng):
   - export dữ liệu 1 user · delete 1 feedback · erase theo `system + user_email`.
   - Lưu ý: `feedback_event` append-only, audit giữ lịch sử (id dangling là cố ý).
3. **Config runtime** (privacy/retention):
   - `ATTACHMENT_RETENTION_DAYS`, privacy flags, `FEEDBACKKB_OPEN_REGISTER`,
     `FEEDBACKKB_SEED_SYSTEMS` — qua env/secret, không sửa code.
4. **Batch sync** feedback cũ từ hệ đã có (idempotent):
   ```bash
   npx feedbackkb sync   # bulk-forward, UNIQUE(system,external_system,external_id) chống trùng
   ```
5. **Onboard consumer không cấp gì** (zero-admin):
   - `auth=none` + `FEEDBACKKB_SEED_SYSTEMS` (kín) hoặc `FEEDBACKKB_OPEN_REGISTER=true`
     (chỉ mạng nội bộ tin cậy).

## An toàn (bắt buộc)
- DB trung tâm dùng chung cụm với FPA → pool giới hạn `DB_POOL_MAX`, **không** chạy `pytest` full nhắm DB prod.
- Cred DB chỉ ở server (env/secret manager), **không** commit, **không** in ra log.
- Việc irreversible (xoá lesson/feedback) → xác nhận rõ trước khi chạy.

## Exit criteria
- [ ] Tác vụ chạy đúng qua admin route, audit ghi lại.
- [ ] Không lộ cred, không đụng connection slot FPA.

## Why
Tách việc admin định kỳ khỏi vòng lặp hằng ngày của dev. Bổ trợ:
`/feedbackkb-onboard` (cấp key ban đầu), `/feedbackkb-fix` (gate apply prod).
