# Setup prompt — FeedbackKB (canonical)

> Dán nguyên khối dưới cho 1 Claude session khác để cài FeedbackKB. Không chứa secret.
> Nguyên tắc cốt lõi: **zero-technical-question** — mọi quyết định kỹ thuật quyết sẵn bằng
> code default; session KHÔNG hỏi user câu kỹ thuật.

```
Setup hệ thống FeedbackKB.

Repo: https://github.com/duongph-ui/feedbackkb  (đã clone ở D:\Clevai\SEPO\Feedback)
Đọc trước: docs/deploy-clevai.md (runbook) + docs/dev-handoff.md.
Cred DB thật: đọc programmatic từ .credentials/Vault.md (PG_PASSWORD) — KHÔNG in ra, KHÔNG commit.

Mô hình: 1 API trung tâm giữ cred DB; client chỉ app_key. DB = schema fbk trong database fna
trên postgres.clevai.vn:5432. Toolchain: python (KHÔNG python3 — stub hỏng), venv packages/server/.venv.

QUAN TRỌNG về cleanup (TỰ QUYẾT, KHÔNG HỎI ANH):
- Đây là SETUP THẬT → GIỮ schema fbk + bảng (deploy cần). TUYỆT ĐỐI không xoá schema/bảng.
- Không chạy pytest nhắm DB prod (đụng slot FPA). Verify bằng API thật, không bằng test suite.
- Smoke tạo 1 feedback test → sau khi xác nhận, xoá đúng row đó bằng id, hết.

Việc:
1. cd packages/server; python -m venv .venv; .venv/Scripts/python -m pip install -e ".[dev]"; pytest (chạy được, DB test tự skip — không đụng prod).
2. Tạo .env: DATABASE_URL=postgresql://fna_user:<PG_PASSWORD>@postgres.clevai.vn:5432/fna ; FEEDBACKKB_AUTH=none ; DB_POOL_MAX=5. (giữ FEEDBACKKB_EMBED=none — semantic AI off, P1-P4 chạy bằng FTS+hash.)
3. Apply schema: python -m yoyo apply --batch --database "$DATABASE_URL" ../../migrations  (idempotent; migration 0002 pgvector cần extension `vector` trên cụm — nếu cụm chưa có thì BỎ QUA 0002, hệ vẫn chạy).
4. uvicorn feedbackkb_server.app:app --port 8000 ; verify GET /healthz = {"status":"ok"}.
5. Smoke (cần 1 mã hệ thống <CODE> do ANH cấp — HỎI ANH, đừng tự đặt; hoặc bật FEEDBACKKB_OPEN_REGISTER=true ở mạng nội bộ):
   POST /api/feedback {"system":"<CODE>","message":"test"} → 200 status new.
   WORKER_ONCE=1 python -m feedbackkb_server.worker → row chuyển triaged.
   Xác nhận xong → xoá đúng row smoke đó.

KẾT THÚC SETUP (BẮT BUỘC làm, KHÔNG để anh treo):
- Nếu 0002 pgvector báo "Must be superuser / InsufficientPrivilege" → ĐÂY LÀ BÌNH THƯỜNG,
  không phải lỗi. Semantic AI (Phase 7) off mặc định; P1-P4 chạy đủ. KHÔNG hỏi anh stop hay không.
- Báo anh: "Cài xong, hệ thống dùng được." rồi CHỈ anh đọc docs/user-guide.md (cài xong giờ làm gì
  + 4 skill). Tóm tắt 4 skill: /feedbackkb-onboard (gắn thu feedback), /feedbackkb-knowledge
  (sửa bug + nhớ bài học), /feedbackkb-fix (agent team lọc), /feedbackkb-ops (admin).
- Muốn bật pgvector sau: nhờ DBA `CREATE EXTENSION vector` 1 lần rồi đổi FEEDBACKKB_EMBED. Không gấp.

QUY TẮC GIAO TIẾP:
- caveman mode, xưng "em" gọi "anh".
- KHÔNG hỏi anh câu kỹ thuật (SQL/schema/tên bảng/pool/adapter). Tự quyết default kỹ thuật từ code + .env.example.
- Chỉ hỏi khi cần GIÁ TRỊ NGHIỆP VỤ anh mới biết (vd mã hệ thống <CODE>), bằng tiếng thường + kèm ví dụ + khuyến nghị 1 lựa chọn — KHÔNG bày option toàn thuật ngữ.
- Mọi commit secret-scan trước (repo PUBLIC). Agent ở .claude/agents/, skill ở .claude/skills/ (clone tự nạp).
```

## Nếu chỉ TÍCH HỢP app (không host server)
Rút gọn: *"Đọc docs/dev-handoff.md → chạy skill /feedbackkb-onboard với mã hệ thống do anh cấp"* —
consumer chỉ cần app_key, không cần cred DB.
