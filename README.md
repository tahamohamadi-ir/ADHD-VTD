# PARS-SQL / VTD-Edge

**Persian-aware, privacy-first, local Text-to-SQL for mental-health and student-lifestyle analytics.**

این پروژه یک سامانه‌ی محلی و قابل‌ارزیابی برای تبدیل پرسش فارسی به SQL امن است. هدف پروژه این نیست که صرفاً یک LLM را به دیتابیس وصل کند؛ هدف ساخت یک pipeline شبیه compiler است که قبل از تولید SQL، سؤال را normalize، route، schema-link، value-link و validate می‌کند و فقط queryهای read-only را اجرا می‌کند.

---

## 1. Current Status

Phase 0 با موفقیت انجام شده است:

```text
✅ Python 3.12.10 environment smoke test passed
✅ SQLite DB opens in read-only mode
✅ Schema snapshot generated and accepted
✅ Value dictionary generated
✅ 50-question Phase 0 audit: 50/50 gold SQL executed successfully
✅ Milestone 1.5 stress-test: 20/20 passed with fallback rule router
✅ Semantic metadata alignment: 11/11 passed
```

نکته مهم: نتیجه‌ی Milestone 1.5 نشان می‌دهد router rule-based اولیه برای stress-test خوب عمل می‌کند؛ اما هنوز اثبات نمی‌کند که LLM، SchemaLinker، ValueLinker و SQL Validator در pipeline کامل درست کار می‌کنند. این repo عمداً قبل از LLM روی foundation تمرکز می‌کند.

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
| Persian normalization | Phase 1 | Implement now |
| Finglish/typo mapping | Phase 1 | Implement now |
| Safety/ambiguity router | Phase 1 | Implement now |
| Value linking | Phase 1 | Implement now |
| SQL safety/syntax validation | Phase 1 | Implement now |
| Read-only executor | Phase 1 | Implement now |
| Basic local LLM generation | Phase 2 | After validators |
| CAG/RAG | Phase 4 | Not before baseline |
| LangGraph full pipeline | Research Phase 8/9 | Not edge default |
| Reflexion / SQL Surgeon | After validated baseline | Not before validators |
| Consistency-based abstention | Paper 1 after multi-candidate | Later |
| Edge state machine | Phase 10+ | Later |

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

## 9. First Implementation Milestone

Do not jump to CAG or Reflexion yet. The next milestone is:

```text
M1: Rule-based NLU + schema/value linking + SQL safety/syntax validation + read-only execution.
```

The goal is to prove that the deterministic foundation can answer:

```text
کاربر چه می‌خواهد؟
آیا سؤال safe است؟
آیا سؤال ambiguous است؟
کدام table/column/value مناسب است؟
آیا SQL فقط SELECT و قابل parse است؟
آیا execution کاملاً read-only است؟
```

Only after this should the local LLM generation layer be added.
