# PARS-SQL / VTD-Edge

**Persian-aware, privacy-first, local Text-to-SQL for mental-health and student-lifestyle analytics.**

این پروژه یک سامانه‌ی محلی و قابل‌ارزیابی برای تبدیل پرسش فارسی به SQL امن است. هدف پروژه این نیست که صرفاً یک LLM را به دیتابیس وصل کند؛ هدف ساخت یک pipeline شبیه compiler است که قبل از تولید SQL، سؤال را normalize، route، schema-link، value-link و validate می‌کند و فقط queryهای read-only را اجرا می‌کند.

---

## 1. Current Status

این پروژه از فازهای پایه عبور کرده و اکنون یک runtime پژوهشی reliability-first با گراف حالتمند دارد:

```text
✅ Phases 0-7: Schema Freeze, NLU, QIR, Schema/Value Linking, SQL Validation Stack,
   Local LLM Layer, Stress Test, Hybrid CAG/RAG Retrieval (Completed)
✅ Phase 8: LangGraph Orchestration (Completed; --checkpoint-db SQLite checkpointing,
   Mermaid diagram export added; retrieve_values helper implemented, not routed)
✅ Phase 9: Graph-Level Reflexion / SQL Repair (Basic)
✅ Phase 10: Benchmark Runner (Completed - infrastructure; artifact contract enforced)
🚧 Phase 11 / 13 / 16: Ablation, Reliability Gate, Semantic Judge (In progress)
🚧 Phase 12: Output, Chart, Narrative (Implemented - code/tests/narrative;
   behavior-benchmark rerun pending user GPU run)
✅ Phase 17: Pipeline & Prompt Optimization (Completed)
🚧 Phase 18.7: Anti-overfit zero/few-shot push toward strict EX >= 65% (In progress)
```

ابزارها و اجزای اخیر (fact پیاده‌سازی، نه نتیجه benchmark):

- holdout ضد-overfit `phase18_7_holdout_paraphrase48.json` و retrieval ablation configs `c0/c1/c2`.
- ablation flag ‏`reliability_gate_routing` برای مقایسه annotation-only در برابر routed gate.
- ‏`CrossEncoderReranker` مدل‌محور با identity fallback و propagation مربوط به retrieval backend/reranker در agent mode.
- زنجیره خروجی مطابق spec در گراف: `recommend_chart -> log_benchmark_record -> END`.
- روایت‌ساز فارسی متصل به answer payloads؛ judge adjudication import و human spot-check package/import با Cohen's kappa.

هر عدد یا ادعای کیفیت فقط از طریق artifact معتبر `results/benchmark/...` گزارش می‌شود.

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
| Reflexion / Self-Correction | Phase 9 | ✅ Basic completed |
| Benchmark Runner | Phase 10 | ✅ Completed (infrastructure) |
| Ablation & Error Analysis | Phase 11 | 🚧 In progress |
| Output / Chart / Narrative | Phase 12 | 🚧 Implemented - code/tests/narrative (behavior rerun pending user GPU run) |
| Multi-candidate / Reliability | Phase 13 | 🚧 In progress (gate routing experiment pending) |
| Edge state machine | Phase 14 | 🚧 Prototype implemented (profiler/caches/EdgePipeline; comparisons pending) |
| Research Packaging | Phase 15 | 🚧 Tooling implemented (bundle/CI/Dockerfile/pre-commit; final packaging pending paper promotion) |
| Pipeline & Prompt Optimization | Phase 17 | ✅ Completed |
| Zero-Shot Mastery Push | Phase 18.7 | 🚧 In progress (anti-overfit push toward strict EX >= 65%) |

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
│   ├── graph/
│   ├── reflexion/
│   ├── utils/
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

تمرکز فعلی پروژه روی Phase 18.7 است و residue فازهای دیگر بعد از آن بسته می‌شود:

```text
Phase 18.7: anti-overfit zero/few-shot push toward strict EX >= 65%
    (holdout paraphrase48 + retrieval c0/c1/c2 ablations + reliability_gate_routing flag)
Phase 12 residue: behavior-benchmark rerun after output-chain integration (user GPU run)
Phase 15 residue: final packaging after paper promotion artifacts
```

برای اجرای سیستم در حالت فعلی:
```powershell
python scripts/run_agent.py "درصد دانشجویان افسرده چقدر است؟" --verbose
```

## 10. Benchmark and Test Guide

برای اجرای تست‌ها و benchmarkها، راهنمای عملی زیر منبع اصلی است:

```text
docs/BENCHMARK_AND_TEST_GUIDE.md
```

نمونه‌های سریع:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\tier1_unit -q
.\.venv\Scripts\python.exe scripts\run_benchmark.py --mode gold --dataset dev --samples-per-level 5 --ablation-id smoke
.\.venv\Scripts\python.exe scripts\run_benchmark.py --mode agent --dataset dev --samples-per-level 1 --ablation-id full_trace
```

خروجی benchmark در `results/benchmark/<timestamp>_<mode>_<dataset>_<model_slug>_<ablation_id>/` ذخیره می‌شود و شامل `config`, `predictions`, `attempts`, `failures`, `summary`, CSVها و جدول‌های اولیه مقاله است.
