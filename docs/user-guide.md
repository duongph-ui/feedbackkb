# FeedbackKB — Cài xong rồi, giờ làm gì?

> Trang này cho người vừa setup xong. Không cần biết SQL/schema. Chỉ cần biết **chạy skill nào**.

## Hệ thống đang chạy được — yên tâm

Nếu setup báo **"pgvector blocked / Must be superuser"** → **KHÔNG sao**, không phải lỗi.
- pgvector = phần **AI ngữ nghĩa nâng cao** (gom feedback trùng theo *ý nghĩa*, gợi ý theme). Tắt mặc định.
- Toàn bộ chức năng chính (thu feedback, phân loại, tìm trùng bằng từ khoá, knowledge, fix) **chạy bình thường thiếu nó**.
- Muốn bật sau: nhờ DBA cài 1 lần (`CREATE EXTENSION vector` trên cụm) → đổi 1 dòng config. Không gấp.

→ Coi như **cài xong = dùng được**. pgvector là tính năng cộng thêm cho sau.

## Hệ thống làm được gì (4 việc)

| Bạn muốn | Chạy skill | Khi nào dùng |
|---|---|---|
| Gắn nút thu feedback vào app của bạn | `/feedbackkb-onboard` | 1 lần cho mỗi app/hệ thống |
| Sửa bug hằng ngày, không quên bài học cũ | `/feedbackkb-knowledge` | Mỗi lần sửa bug: tra bài cũ → fix → ghi bài mới |
| Để agent team tự phân loại + đề xuất fix | `/feedbackkb-fix` | Khi hàng đợi feedback nhiều, muốn máy lọc trước |
| Việc admin: xoay key, GDPR, dọn dữ liệu cũ | `/feedbackkb-ops` | Định kỳ, cần quyền admin |

## Luồng thường gặp

**1. Lần đầu — gắn thu feedback vào 1 app**
```
/feedbackkb-onboard
```
Skill hỏi **mã hệ thống** (ví dụ `FPS`, `FPA` — tên ngắn cho app của bạn) → cấp app_key → nhúng widget. Xong: app gửi được feedback thật về DB trung tâm.

**2. Hằng ngày — dev sửa bug**
```
/feedbackkb-knowledge
```
Vòng: **search** (có ai gặp bug này chưa?) → **fix** → **capture** (ghi lại cách sửa). Lần sau gặp lại thì search ra ngay. Đây là giá trị lớn nhất — bài học không rò rỉ.

**3. Có nhiều feedback dồn — để máy lọc**
```
/feedbackkb-fix
```
Agent team (Conductor điều phối) tự **phân loại → phân tích → đề xuất fix**, rồi **DỪNG** chờ người duyệt việc nguy hiểm (apply lên prod / merge / xoá). Người chỉ gật/lắc.

## Kiểm tra nhanh hệ thống sống

- Mở `http://localhost:8000/healthz` → thấy `{"status":"ok"}` = server sống.
- Gửi thử 1 feedback qua widget (sau onboard) → vào hàng đợi `new`.
- Chạy worker 1 nhịp → feedback chuyển `triaged`. Phân loại chạy.

## Bật AI ngữ nghĩa sau này (tùy chọn)

Khi DBA đã cài `vector` trên cụm:
1. Re-apply migration (lệnh trong [deploy-clevai.md](deploy-clevai.md)).
2. Đổi config `FEEDBACKKB_EMBED` từ `none` sang `openai` (hoặc `local`).
3. Mở thêm: gom feedback trùng theo ý nghĩa, tìm knowledge theo ngữ nghĩa, bảng theme `/api/themes`.

Không bật cũng không sao — P1–P4 đầy đủ.

## Đọc thêm

- [integration-guide.md](integration-guide.md) — nhúng widget vào app cụ thể
- [deploy-clevai.md](deploy-clevai.md) — runbook deploy + migration
- [dev-handoff.md](dev-handoff.md) — bàn giao cho dev mới
