# PARS-SQL - Phase Documentation Index

این پوشه مستندات اجرایی فازهای توسعه پروژه را نگه می‌دارد. هر فایل phase باید نشان دهد چه چیزی ساخته شده، چطور اجرا می‌شود، چه تستی دارد و چه کاری هنوز باقی مانده است.

## فازهای مستند شده

| Phase | عنوان | وضعیت | فایل |
|---|---|---|---|
| Phase 1 | Fix Foundation Gaps | Completed | [PHASE_1_FOUNDATION_GAPS.md](PHASE_1_FOUNDATION_GAPS.md) |
| Phase 2 | Data & Schema Quality Hardening | Completed | [PHASE_2_DATA_QUALITY.md](PHASE_2_DATA_QUALITY.md) |
| Phase 3 | NLU v2 (Value Linking & QIR) | Completed | [PHASE_3_NLU_QIR.md](PHASE_3_NLU_QIR.md) |
| Phase 4 | SQL Validation Stack | Completed | [PHASE_4_SQL_VALIDATION.md](PHASE_4_SQL_VALIDATION.md) |
| Phase 5 | Local LLM Generation Layer | Completed | [PHASE_5_LOCAL_LLM_GENERATION.md](PHASE_5_LOCAL_LLM_GENERATION.md) |
| Phase 6 | Milestone 1.5 Stress Test | Completed | [PHASE_6_STRESS_TEST.md](PHASE_6_STRESS_TEST.md) |
| Phase 7 | Hybrid CAG/RAG Retrieval | Completed | [PHASE_7_RETRIEVAL.md](PHASE_7_RETRIEVAL.md) |
| Phase 10 | Benchmark Runner | In progress | [PHASE_10_BENCHMARK_RUNNER.md](PHASE_10_BENCHMARK_RUNNER.md) |

## فازهای نیازمند سند مستقل

| Phase | عنوان | وضعیت سند |
|---|---|---|
| Phase 8 | LangGraph Orchestration | TODO |
| Phase 9 | Reflexion, SQL Surgeon, Semantic Critic | TODO |
| Phase 11 | Ablation, Error Analysis, Research Metrics | TODO |
| Phase 12 | Output, Chart, Narrative | TODO |
| Phase 13 | Reliability Gate, Multi-Candidate, Abstention | TODO |
| Phase 14 | Edge Runtime | TODO |
| Phase 15 | Research Packaging | TODO |

## قالب پیشنهادی هر phase document

1. هدف فاز و مسئله‌ای که حل می‌کند.
2. فایل‌های تغییر یافته یا اضافه شده.
3. جریان runtime یا data flow.
4. دستورهای اجرا و تست.
5. معیار پذیرش.
6. محدودیت‌های فعلی و کارهای بعدی.
