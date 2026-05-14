# PARS-SQL — Phase Documentation Index

> این پوشه شامل مستندات کامل هر فاز توسعه پروژه PARS-SQL / VTD-Edge است.  
> هر فاز شامل جزئیات پیاده‌سازی، راهنمای استفاده، و task list فاز بعدی است.

---

## فازهای تکمیل‌شده

| فاز | عنوان | وضعیت | فایل |
|---|---|---|---|
| Phase 0 | Schema Freeze & 50Q Audit | ✅ تکمیل (قبلی) | — |
| **Phase 1** | **Fix Foundation Gaps** | **✅ تکمیل** | [PHASE_1_FOUNDATION_GAPS.md](PHASE_1_FOUNDATION_GAPS.md) |
| **Phase 2** | **Data & Schema Quality Hardening** | **✅ تکمیل** | [PHASE_2_DATA_QUALITY.md](PHASE_2_DATA_QUALITY.md) |

## فازهای در انتظار

| فاز | عنوان | وضعیت | فایل |
|---|---|---|---|
| **Phase 3** | **NLU v2 (Value Linking & QIR)** | **🔜 آماده** | — |
| Phase 4 | SQL Validation Stack کامل | ⏳ | — |
| Phase 5 | Local LLM Generation Layer | ⏳ | — |
| Phase 6 | Milestone 1.5 Stress Test | ⏳ | — |
| Phase 7 | Hybrid CAG/RAG Retrieval | ⏳ | — |
| Phase 8 | LangGraph Orchestration | ⏳ | — |
| Phase 9 | Reflexion, SQL Surgeon, Semantic Critic | ⏳ | — |
| Phase 10 | Benchmark Runner کامل | ⏳ | — |
| Phase 11 | Ablation, Error Analysis, Research Metrics | ⏳ | — |
| Phase 12 | Output, Chart, Narrative | ⏳ | — |
| Phase 13 | Reliability Gate, Multi-Candidate, Abstention | ⏳ | — |
| Phase 14 | Edge Runtime (اختیاری) | ⏳ | — |
| Phase 15 | Research Packaging | ⏳ | — |

---

## قالب هر Phase Document

هر فایل Phase شامل بخش‌های زیر است:

1. **هدف فاز** — چه مشکلی حل می‌شود
2. **فایل‌های تغییریافته** — جدول کامل با وضعیت قبل/بعد
3. **جزئیات هر کامپوننت** — API Reference, مثال‌ها, طراحی
4. **Unit Tests** — لیست تست‌ها و نتایج
5. **پیشنهادات بهبود** — چه چیزهایی می‌تواند بهتر شود
6. **وابستگی‌ها** — ارتباط با فازهای دیگر
