---
name: feedbackkb-onboard
description: Onboard MỘT lần một hệ thống vào FeedbackKB — cấp app_key, nhúng widget thu feedback vào app của dev, cắm MCP + hook + rules. Feedback luôn ghi/đọc trên Postgres trung tâm đã tạo (không tự dựng DB). Chạy 1 luồng từ đầu tới khi widget gửi được feedback thật.
---

# /feedbackkb-onboard

Gộp **setup + tích hợp tính năng feedback** thành **1 lần onboard cho mỗi hệ thống**.
Sau skill này: app của dev có nút "Phản hồi" gửi feedback thẳng vào **DB Postgres trung tâm**,
và Claude Code trong repo tra/ghi được knowledge.

> **Nguyên tắc cố định (không hỏi lại):**
> - **Intake mặc định = Widget** `@clevai/feedbackkb-widget` → API trung tâm → **Postgres đã tạo** (`fbk.*`).
> - Dev **KHÔNG** dựng DB, **KHÔNG** chạm SQL, **KHÔNG** cầm cred DB. Chỉ cầm `app_key`.
> - Mọi feedback của mọi hệ thống đều lấy/ghi trên **cùng 1 DB trung tâm** (multi-tenant theo `system`).

## Inputs cần hỏi dev (tối thiểu)
1. `system` code (vd `FPS`) + `name` (vd "Payment System").
2. App của dev build kiểu gì: **React (bundler)** hay **không bundler** (dùng bản CDN `<script>`).
3. URL API trung tâm (mặc định `https://fpa.mikai.tech` nếu chưa có).

## Steps (1 luồng)
1. **Register → app_key**
   ```bash
   npx feedbackkb register --system <CODE> --name "<Name>" --api <API_URL>
   #   → fbk_live_xxx  (lưu vault/secret, KHÔNG commit)
   ```
   Nếu chạy `auth=none` (mạng nội bộ) thì bỏ qua key — chỉ cần system tồn tại (seed/open-register).
2. **Nhúng widget vào app dev** (tính năng feedback cho end-user)
   - React: `npm i @clevai/feedbackkb-widget` rồi mount 1 lần ở layout:
     ```tsx
     import { FeedbackWidget } from "@clevai/feedbackkb-widget";
     <FeedbackWidget system="<CODE>" apiBase="<API_URL>" appKey="<app_key>" />
     ```
   - Không bundler: chèn 1 thẻ `<script>` bản CDN + `data-system` / `data-api` / `data-key`.
3. **Cắm MCP** (dev tra/ghi knowledge trong IDE)
   ```bash
   npx feedbackkb init-mcp --key <app_key> --api <API_URL>   # ghi block .mcp.json
   ```
4. **Cắm Stop-hook** (auto rút lesson cuối session)
   ```bash
   npx feedbackkb init-hook
   ```
5. **Cắm rules** (CLAUDE.md routing: ưu tiên search_knowledge trước khi fix)
   ```bash
   npx feedbackkb init-rules
   ```
6. **Verify 1 vòng end-to-end**
   - Mở app → bấm "Phản hồi" → gửi 1 feedback test → nhận "Đã ghi nhận".
   - `list_feedback` (MCP) hoặc dashboard thấy bản ghi `status=new` trên **DB trung tâm**.
   - Xác nhận feedback nằm đúng `system` của mình (tenant-scoped).

## Exit criteria
- [ ] `app_key` cấp + lưu an toàn (hoặc auth=none đã seed system).
- [ ] Widget mount, gửi được feedback thật → xuất hiện trong DB trung tâm.
- [ ] `.mcp.json` + Stop-hook + CLAUDE.md rules đã ghi.
- [ ] Dev KHÔNG được cấp quyền/cred Postgres nào.

## Why
Một lần onboard = vừa bật kênh feedback cho end-user, vừa bật knowledge-loop cho dev.
DB trung tâm là ranh giới quyền: dev chỉ nói chuyện qua HTTP + `app_key`.
Tiếp theo: dùng `/feedbackkb-knowledge` (hằng ngày) và để agent chạy `/feedbackkb-fix`.
