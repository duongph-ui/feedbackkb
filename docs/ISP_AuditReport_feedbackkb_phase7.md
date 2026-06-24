# ISP Audit Report — FeedbackKB Phase 7 (P5 Nâng AI) · diff-mode

> T230 AuditISP · scope = delta Phase 7 (Steps 42–48) thêm bởi BuildISP từ AP P5 + decisions #9/#10.
> Bản gốc 44 step (Phase 0–6) đã audit ở `ISP_AuditReport_feedbackkb.md` — không re-audit.

## 1. Audit summary
- Steps audited: **7** (42–48)
- **PASS 1 · ENRICH 6 · BLOCK 0**
- Coverage AP P5 → ISP: **100%** (semantic dedup, semantic search, pgvector store, fixability score, theme quantification, zero-tech-setup đều có step).
- 0 BLOCK → không có câu hỏi chặn cho user; mọi ENRICH đã tự bù từ AP + research (Seer/Enterpret/Unwrap) + default an toàn.

## 2. Coverage matrix (AP P5 → ISP)
| AP nguồn | ISP step |
|---|---|
| §4 P5 "Semantic dedup (pgvector+embeddings)" + decision #10 | 42 (store), 43 (embed), 44 (dedup) |
| §4 P5 semantic retrieve-before-fix | 45 |
| §4 P5 "Fixability/confidence score gate" (như Seer) + #10 | 46 |
| §4 P5 "theme quantification theo thời gian" | 47 |
| §3.5.4 + decision #9 zero-tech-question setup | 48 |

## 3. Audit table (7-criteria)
| Step | Name | Data | API | UI | Logic | AC | Lib | Deps | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| 42 | pgvector migration | ✅ | — | — | ✅ | ✅ | ⚠️ | ✅ | ENRICH |
| 43 | embedding provider | ✅ | ⚠️ | — | ✅ | ✅ | ❌ | ✅ | ENRICH |
| 44 | semantic dedup | ✅ | — | — | ⚠️ | ✅ | ✅ | ✅ | ENRICH |
| 45 | semantic search_knowledge | ✅ | ✅ | — | ⚠️ | ✅ | ✅ | ✅ | ENRICH |
| 46 | fixability score gate | ✅ | — | — | ❌ | ✅ | — | ✅ | ENRICH |
| 47 | theme quantification | ✅ | ✅ | ⚠️ | ❌ | ✅ | — | ✅ | ENRICH |
| 48 | zero-tech-question guard | ✅ | — | — | ✅ | ✅ | — | ✅ | PASS |

## 4. Detailed findings + enrichment (đã áp vào ISP)
- **42** thiếu Lib/dim → ENRICH: `EMBED_DIM` mặc định 1536; index HNSW `vector_cosine_ops`; pgvector ≥0.7.
- **43** thiếu model/SDK → ENRICH: adapter `openai`(text-embedding-3-small/1536) | `local`(all-MiniLM-L6-v2/384) | `none`; `EMBED_DIM` khớp adapter; cache theo symptom_hash.
- **44** thiếu ngưỡng cosine → ENRICH: dup khi cosine ≥ 0.85 (distance ≤ 0.15), top-k=10/system/30 ngày; embed off → FTS Step 25.
- **45** thiếu top-k → ENRICH: top-k=10 rank cosine (không cắt ngưỡng cứng); embed off → ILIKE.
- **46** thiếu công thức/ngưỡng → ENRICH: score = 0.4·lesson_match + 0.25·grounding + 0.2·dedupe + 0.15·severity; `FIXABILITY_MIN`=0.6 → auto/need_human; KHÔNG vượt gate prod.
- **47** thiếu thuật toán cluster → ENRICH: incremental online (centroid gần nhất cosine ≥ 0.8 else theme mới), window tuần, running-mean.
- **48** PASS — test/lint pattern rõ, deterministic.

## 5. Enriched steps
→ Đã ghi trực tiếp dòng **Enriched (T230)** vào `docs/IncrementalStepPlan_feedbackkb.md` (Steps 42–47). Step 48 giữ nguyên (PASS).

## 6. Open questions (BLOCK)
**Không có.** 0 BLOCK. Lưu ý non-blocking khi build P5: model embedding (#43) tuỳ ngân sách/độ riêng tư — default `none` (off) an toàn, bật `local` nếu không muốn gọi API ngoài; quyết khi thực sự build Phase 7 (sau volume), không chặn V1.

## 7. Sign-off
- ISP Quality Auditor: ✅ Phase 7 — 6 ENRICH applied, 1 PASS, 0 BLOCK; coverage P5 100%.
- Software Architect: ✅ fallback an toàn xuyên suốt (embed off → P1–P4 cũ); human gate apply-prod bất biến (score không bypass); DAG no-cycle.
- Verdict: **Phase 7 ready for T310 build** khi tới P5 (sau khi có volume thật).
