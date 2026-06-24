# Kế hoạch: Hệ thống Feedback + Knowledge Capture (multi-agent)

> Trạng thái: **PLAN — chờ review, chưa build**
> Ngày: 2026-06-24 · Owner: duongph

## 1. Bối cảnh & Nỗi đau

Team xây hệ thống internal bằng Claude. Hai nỗi đau:

1. **Mất tri thức**: dev sửa lỗi bằng cách prompt trực tiếp Claude, không ghi lại kinh nghiệm/nguyên nhân gốc → lỗi tương tự lặp lại, người mới không học được.
2. **Không có kênh feedback**: user dùng hệ thống gặp lỗi nhưng không có chỗ gửi phản hồi, lỗi không được ghi nhận có hệ thống.

## 2. Mục tiêu

Dựng bộ **skill + agent team + MCP** làm **một nơi** vừa:
- Thu nhận & lưu **kinh nghiệm sửa lỗi** (bug-fix knowledge).
- Ghi nhận **feedback user** và xử lý dần.

Triết lý multi-agent: **con người đưa mục tiêu**, agent làm việc tầng dưới + tự quyết định, **chỉ hỏi người ở quyết định quan trọng**.

## 3. Quyết định kiến trúc đã chốt

| Hạng mục | Lựa chọn |
|---|---|
| Kho knowledge | **sepo-mcp wiki** (tag-tree + semantic search) |
| Kênh feedback | **Widget trong app → API chung** |
| Feedback store | **Postgres bảng `feedback`** |
| Mức tự chủ agent | **Triage tự động, fix cần duyệt** |
| Hệ thống pilot | **FPS** (đang UAT, nhiều feedback) |

## 4. Kiến trúc tổng

```
[User trong app] --widget--> [Feedback API] --> [Postgres: feedback]
                                                        |
[Dev fix bug] --skill/hook capture----------------------+
                                                        v
                                            [Agent Team triage/fix]
                                                        |
                                                        v
                                        [sepo-mcp wiki: knowledge]
```

## 5. Phần 1 — Feedback intake (widget → API → Postgres)

### 5.1 Feedback API (service chung)
- Endpoint: `POST /feedback`
- Body: `{ system, user, page_url, type(bug|idea|question), message, screenshot?, context(version/env) }`
- Status machine: `new → triaged → in_progress → resolved → wontfix`

### 5.2 Bảng Postgres `feedback` (schema nháp)
| Cột | Kiểu | Ghi chú |
|---|---|---|
| id | uuid pk | |
| system | text | "FPS", "FPA"... |
| user_email | text | |
| page_url | text | auto từ widget |
| type | text | bug/idea/question |
| message | text | |
| screenshot_url | text | nullable |
| context | jsonb | version, env, browser |
| severity | text | agent gán |
| status | text | new/triaged/... |
| knowledge_ref | text | link doc wiki liên quan |
| created_at | timestamptz | |

### 5.3 Widget nhúng
- 1 snippet (React component / JS) drop vào mỗi app.
- Nút nổi "Gửi phản hồi" → form → auto-attach `page_url`, app version, user.
- Mỗi app chỉ thêm: 1 import + config `{ system: "FPS" }`.

## 6. Phần 2 — Knowledge capture

### 6.1 Schema knowledge (sepo-mcp wiki)
- Tags: `['KB', <system>, <category>]` → auto folder-tree.
- 1 doc / lesson, cấu trúc cố định:
  - **Triệu chứng** (symptom user/dev thấy)
  - **Nguyên nhân gốc** (root cause)
  - **Fix** (làm gì)
  - **File / dòng** liên quan
  - **Cách phòng** (prevent tái diễn)
- Semantic search có sẵn → tìm "lỗi tương tự" trước khi prompt mới.

### 6.2 Auto-capture (không phụ thuộc dev tự giác)
- **Skill `/capture-fix`** (chủ động): dev gõ sau khi fix → agent đọc git diff + hội thoại → sinh lesson doc → đẩy wiki. 1 lệnh.
- **Stop hook** (bị động): cuối session có sửa code → nhắc/tự rút lesson, bắt cái dev quên.

## 7. Phần 3 — Agent Team (triage auto, fix cần duyệt)

| Agent | Việc | Tự quyết / Hỏi người |
|---|---|---|
| Collector | Poll feedback `new`, gom + dedupe | Tự |
| Triage | Phân loại bug/idea/dup, gán severity + system, link knowledge cũ | Tự |
| Investigator | Lần root cause, định vị file:line (read-only) | Tự |
| Fixer | Soạn fix + viết lesson, mở PR draft | **Hỏi** trước khi apply prod |
| Curator | Đẩy lesson vào wiki, gộp trùng | Tự |

- Orchestrator: human đưa goal ("xử feedback tuần này") → chạy pipeline → chỉ hỏi ở mốc quan trọng (apply prod, severity cao, conflict).
- Triển khai bằng Workflow tool / agent-team.

## 8. Thứ tự dựng (tăng dần, giá trị sớm)

1. **Schema knowledge + skill `/capture-fix`** → knowledge tích lũy ngay, 0 đụng app.
2. **Feedback API + Postgres + 1 widget pilot trên FPS**.
3. **Collector + Triage agent** → đọc feedback, phân loại, link knowledge.
4. **Investigator + Fixer + Curator** → vòng fix bán tự động.
5. Nhân widget ra các app còn lại (FPA, HRMS...).

## 9. Điểm cần làm rõ thêm (mở)
- API host ở đâu? (chung hạ tầng mikai.tech như FPS staging?)
- Auth widget: dùng session app sẵn hay token riêng?
- Postgres: schema riêng `feedback.*` hay nhét chung DB FPS?
- Quyền đẩy wiki: agent dùng API key sepo-mcp nào?
```
