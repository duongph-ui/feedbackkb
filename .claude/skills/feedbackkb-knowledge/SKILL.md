---
name: feedbackkb-knowledge
description: Luồng knowledge hằng ngày của dev — TRA lesson cũ trước khi fix, fix, rồi GHI lesson lại. Giải nỗi đau #1 (knowledge rò rỉ khỏi prompt lẻ). Đọc/ghi trên DB trung tâm qua MCP, không chạm SQL.
---

# /feedbackkb-knowledge

Vòng lặp tri thức cho mỗi lần dev sửa bug: **search → fix → capture**. Tất cả qua
`feedbackkb-mcp` (REST → Postgres trung tâm), dev không viết SQL.

## Steps (1 luồng)
1. **Search trước khi fix** — đừng debug lại từ đầu:
   ```
   search_knowledge("<triệu chứng lỗi>", system="<CODE>")
   ```
   Có lesson cũ → tái dùng cách fix; không có → sang bước 2.
2. **Fix code** như bình thường.
3. **Capture lesson** — gọi `/capture-fix` (skill riêng) hoặc trực tiếp:
   ```
   capture_lesson(system, category, symptom, root_cause, fix, files, prevent)
   ```
   - Lesson do dev duyệt → lưu `status=trusted` ngay.
   - Trùng gần đúng → bump `occurrence`, không tạo mới (dedupe theo `symptom_hash`).
4. **(Tuỳ) Link feedback** — nếu lesson sinh từ 1 feedback:
   ```
   link_knowledge(feedback_id, store_ref)
   ```

## Noise filter
Bỏ fix tầm thường (typo/format không có giá trị phòng ngừa). Stop-hook
(`.claude/agents/hooks/capture-lesson.sh`) là phần bị động bắt các fix dev quên ghi.

## Exit criteria
- [ ] Đã search trước khi fix (không trùng công).
- [ ] Lesson 5 mục ghi vào DB trung tâm, dedupe đúng.
- [ ] (nếu có) feedback đã link tới lesson.

## Why
Đây là **trục xương sống của dev** với FeedbackKB. Tra/ghi ngay trong IDE giữ
knowledge không rời flow. Bổ trợ: `/capture-fix` (ghi), `/feedbackkb-onboard` (cài MCP).
