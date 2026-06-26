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

## CHỈ hỏi user 1 thứ (giá trị nghiệp vụ)
**Mã hệ thống** + tên — tên ngắn cho app muốn gắn feedback.
> Hỏi bằng tiếng thường, kèm ví dụ + gợi ý, KHÔNG dùng từ kỹ thuật:
> *"App nào anh muốn gắn nút thu phản hồi? Cho em 1 mã ngắn + tên — ví dụ `FPS` = Payment System, `FPA` = Analytics. App của anh mã gì?"*

**TUYỆT ĐỐI KHÔNG hỏi user** (skill tự quyết hết — xem bảng dưới):

| Quyết định kỹ thuật | Skill TỰ làm, KHÔNG hỏi |
|---|---|
| API URL | mặc định `https://fpa.mikai.tech`; nếu repo có `.env` ghi API khác thì dùng nó |
| React hay không-bundler | đọc `package.json`: có `react`/`next`/`vite` → widget npm; không → CDN `<script>` |
| auth=appkey hay none | thử `register`; API trả key → appkey; API offline/nội bộ → `auth=none` + seed system |
| widget chưa publish npm (version 0.0.0) | fallback **link local**: `npm i <đường-dẫn>/packages/widget` hoặc copy bản CDN tay; KHÔNG báo lỗi, KHÔNG hỏi |
| MCP/hook/rules | luôn cắm hết (init-mcp + init-hook + init-rules); không hỏi có cắm không |

→ Nếu BẤT KỲ bước kỹ thuật nào kẹt → **tự chọn fallback an toàn rồi tiếp**, ghi 1 dòng "em tự quyết X vì Y" vào báo cáo cuối, KHÔNG dừng hỏi anh.

## Steps (1 luồng — tự chạy)
0. **Auto-detect** (im lặng): đọc `package.json` (framework) + `.env`/`.mcp.json` (API URL) + `packages/widget/package.json` (đã publish chưa). Quyết các giá trị ở bảng trên.
1. **Register → app_key**
   ```bash
   npx feedbackkb register --system <CODE> --name "<Name>" --api <API_URL>
   #   → fbk_live_xxx  (lưu vault/secret, KHÔNG commit)
   ```
   API offline / nội bộ → bỏ key, set `auth=none` + seed system (skill tự quyết, không hỏi).
2. **Nhúng widget vào app dev** (tính năng feedback cho end-user)
   - React: `npm i @clevai/feedbackkb-widget` rồi mount 1 lần ở layout:
     ```tsx
     import { FeedbackWidget } from "@clevai/feedbackkb-widget";
     <FeedbackWidget system="<CODE>" apiBase="<API_URL>" appKey="<app_key>" />
     ```
   - Không bundler: chèn 1 thẻ `<script>` bản CDN + `data-system` / `data-api` / `data-key`.
   - **Widget chưa publish npm** (version 0.0.0) → link local: `npm i <repo>/packages/widget` (hoặc `pnpm add link:...`); nếu vẫn kẹt → dùng bản CDN tay. Tự làm, không hỏi.
3. **Cắm MCP** (dev tra/ghi knowledge trong IDE)
   ```bash
   npx feedbackkb init-mcp --key <app_key> --api <API_URL>   # ghi block .mcp.json
   ```
4. **Cắm hook tự-động** (2 rule chạy KHÔNG cần gõ tay)
   ```bash
   npx feedbackkb init-hook
   ```
   Ghi 2 hook vào `.claude/settings.json`:
   - `UserPromptSubmit` → `hook-presearch`: prompt có ý-định-fix → ép gọi `search_knowledge` TRƯỚC khi sửa.
   - `Stop` → `hook-capture`: phiên có đổi code → block 1 lần, ép `/capture-fix` ghi lesson trước khi kết phiên (chống loop qua `stop_hook_active`).
5. **Cắm rules** (fallback mềm — CLAUDE.md routing, phòng khi hook tắt)
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
