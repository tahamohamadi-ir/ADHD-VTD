# PARS-SQL / VTD-Edge

**Persian-aware, privacy-first, local Text-to-SQL for mental-health and student-lifestyle analytics.**

این پروژه یک سامانه‌ی محلی و قابل‌ارزیابی برای تبدیل پرسش فارسی به SQL امن است. هدف پروژه این نیست که صرفاً یک LLM را به دیتابیس وصل کند؛ هدف ساخت یک pipeline شبیه compiler است که قبل از تولید SQL، سؤال را normalize، route، schema-link، value-link و validate می‌کند و فقط queryهای read-only را اجرا می‌کند.

---

## 1. Current Status

Phase 0 با موفقیت انجام شده است:

```text
پروژه با موفقیت از فازهای پیاده‌سازی اولیه عبور کرده و اکنون دارای یک پایپ‌لاین هوشمند و شتاب‌دهی شده است:

```text
✅ Phase 0: Schema Freeze & Audit (50/50 gold SQL passed)
✅ Phase 1-4: NLU, QIR, Schema Linking & Validation Stack (Completed)
✅ Phase 5: Local LLM Layer (GPU-accelerated Qwen-7B, 12x speedup achieved)
✅ Phase 8: LangGraph Orchestration (Stateful research runtime implemented)
✅ Phase 9: Reflexion Loop (Self-correction logic for SQL repair active)
✅ Milestone 1.5: Stress-test passed with 100% safety rejection
```

**دستاورد کلیدی اخیر:** انتقال از یک سیستم خطی ساده به یک گراف حالتمند (Agentic) که قادر به تشخیص ابهام، خوداصلاحی در صورت بروز خطای SQL و پاسخ‌دهی سریع روی GPU لپ‌تاپ (GeForce RTX 3050) است.

---

## 2. Architecture Principle

```text
Persian question
  -> Persian normalization
  -> number/date normalization
  -> colloquial/Finglish mapping
  -> safety detection
  -> ambiguity detection
  -> intent classification
  -> schema linking
  -> value linking
  -> SQL generation candidate
  -> SQL safety/syntax/schema validation
  -> read-only SQLite execution
  -> result formatting / abstention / warning
```

The LLM is only a **candidate SQL generator**. It is never trusted as the source of truth for safety, schema correctness, or execution permission.

---

## 3. Feature Decision Table

| Feature | Milestone | Decision |
|---|---|---|
| Schema freeze | Phase 0 | Done |
| Value dictionary | Phase 0 | Done |
| 50Q audit | Phase 0 | Done |
| Semantic metadata alignment | Phase 0 | Done |
| Persian normalization | Phase 1 | Done |
| Finglish/typo mapping | Phase 1 | Done |
| Safety/ambiguity router | Phase 1 | Done |
| Value linking | Phase 3 | Done |
| SQL safety/syntax validation | Phase 4 | Done |
| Read-only executor | Phase 4 | Done |
| Basic local LLM generation | Phase 5 | Done |
| Hybrid CAG/RAG | Phase 7 | Done |
| Reflexion / Self-Correction | Phase 9 | ✅ COMPLETED (Advanced Critic/Planner) |
| Benchmark Runner | Phase 10 | ⚡ 90% (Full Agent Mode) |
| Ablation & Error Analysis | Phase 11 | ⚡ 20% (Ablation Control) |
| Multi-candidate / Reliability | Phase 13 | In Progress |
| Edge state machine | Phase 14 | Later |

---

## 4. Repository Structure

```text
ADHD-VTD/
├── data/
│   ├── db/
│   ├── schema/
│   ├── questions/
│   ├── golden_sql/
│   ├── rag/
│   └── audit/
├── docs/
├── models/
├── scripts/
├── src/
│   ├── config/
│   ├── core/
│   ├── db/
│   ├── nlu/
│   ├── schema/
│   ├── sql_validation/
│   ├── generation/
│   ├── retrieval/
│   ├── evaluation/
│   └── output/
└── tests/
```

---

## 5. Setup on Windows PowerShell

```powershell
cd D:\Project\ADHD-VTD
.\.venv\Scripts\Activate.ps1

$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

python .\scripts\smoke_test_environment.py
python .\scripts\phase0_validate_semantic_metadata.py
```

---

## 6. Phase 1 Foundation Checks

After applying the Phase 1 foundation package, run:

```powershell
python .\scripts\test_phase1_foundation.py
python .\scripts\test_nlu_pipeline.py
python .\scripts\test_value_linker.py
python .\scripts\test_sql_validators.py
python .\scripts\test_read_only_executor.py
```

Expected result:

```text
✅ Phase 1 foundation checks passed.
```

---

## 7. Local Model Policy

The operational target is local/private execution on light hardware such as clinic laptops, tablets, patient/parent devices, and eventually mobile/smartwatch-class devices as hardware improves.

Recommended operational candidates:

```text
Mobile/tablet target: Qwen2.5-Coder-1.5B or Qwen3-1.7B
Clinic laptop target: Qwen2.5-Coder-3B or Phi-4-mini
Best local accuracy target: Qwen2.5-Coder-7B
SQL-specialized baseline: SQLCoder-7B
Cloud upper-bound baseline: GPT-4.1 / DeepSeek / Qwen3-235B
```

Cloud models must be used only for synthetic/de-identified benchmarking, not private clinical data.

---

## 8. Safety and Privacy

This project is not a diagnostic medical system. It supports aggregate analytics over research/demo datasets. Unsafe requests, schema-out-of-scope requests, ambiguous requests, and raw sensitive data retrieval must be rejected or clarified before SQL execution.

Read-only execution is mandatory:

```text
SQLite URI mode=ro
PRAGMA query_only=ON
Only SELECT/WITH SELECT
No INSERT/UPDATE/DELETE/DROP/ALTER/CREATE/PRAGMA/ATTACH/VACUUM
No multiple statements
No SELECT * for sensitive raw retrieval
LIMIT required for raw row retrieval
```

---

## 9. Next Implementation Milestone

پس از تثبیت گراف و لایه تولید، تمرکز پروژه بر روی موارد زیر است:

```text
M2: Full Benchmark Runner & Error Analysis (Phase 10)
M3: Ablation Studies & Research Metrics (Phase 11)
M4: Output Formatting & Data Storytelling (Phase 12)
```

برای اجرای سیستم در حالت فعلی:
```powershell
python scripts/run_agent.py "درصد دانشجویان افسرده چقدر است؟" --verbose
```
