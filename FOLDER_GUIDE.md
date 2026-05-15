# راهنمای آموزشی پوشه‌های پروژه

این فایل نقشه سریع READMEهای محلی پروژه است. هدف READMEهای داخل هر پوشه این است که پروژه علاوه بر کد اجرایی، مثل یک پروژه آموزشی هم خوانده شود: هر پوشه توضیح می‌دهد چه نقشی دارد، چه فایل‌هایی در آن مهم‌اند، چه نکته فنی باید از آن یاد گرفت و مرحله بعد توسعه آن چیست.

## ترتیب پیشنهادی مطالعه

1. `README.md` ریشه برای هدف پروژه و اجرای سریع.
2. `DEVELOPMENT_ROADMAP.md` برای نقشه راه اجرایی از وضعیت فعلی به نسخه research-grade.
3. `task.md` برای checklist خام phaseها.
4. `docs/00_INDEX.md` برای نقشه سندهای معماری.
5. `docs/08_PROJECT_STRUCTURE_AND_FILE_MAP.md` برای source-of-truth ساختار پوشه‌ها.
6. `docs/09_DATASET_AND_EVALUATION_FILES_GUIDE.md` برای source-of-truth dataset و evaluation artifacts.
7. `docs/phases/PHASE_10_BENCHMARK_RUNNER.md` برای قرارداد اجرای benchmark، trace و artifactها.
8. `docs/BENCHMARK_AND_TEST_GUIDE.md` برای اجرای عملی تست‌ها و benchmarkها.
9. `docs/11_SEMANTIC_BUSINESS_LOGIC_EVALUATION.md` برای ارزیابی business correctness و LLM-as-a-Judge.
10. `src/README.md` برای معماری کد و مسیر pipeline.
11. `src/evaluation/README.md` برای benchmark، metric، reliability و ablation.
12. `src/retrieval/README.md` برای جزئیات Hybrid RAG و نحوه بازیابی مثال‌ها.
13. `src/graph/README.md` برای منطق LangGraph و نودهای اجرایی.
14. `data/README.md` برای دیتابیس، schema، dataset، golden SQL و RAG artifacts.
15. `tests/README.md` و `results/README.md` برای ارزیابی، regression و گزارش‌گیری.

## محدوده پوشش

برای پوشه‌های مالکیت‌پذیر پروژه README محلی اضافه شده است: `src`، `data`، `docs`، `scripts`، `tests`، `benchmark`، `experiments`، `results`، `models`، `archive`، `logs`، `scratch` و زیرپوشه‌های کاربردی آن‌ها.

پوشه‌های cache و محیط مثل `.git`، `.venv`، `.idea`، `.pytest_cache`، `.ruff_cache`، `__pycache__` و `.cache/huggingface` عمداً README آموزشی مستقل نگرفته‌اند؛ این‌ها منطق پروژه نیستند و با ابزارها بازتولید می‌شوند.

ساختار کلیدی پروژه:

```text
├── data/
│   ├── db/                 # Read-only SQLite database (patient data)
│   ├── schema/             # Semantic metadata and DDL specs
│   ├── questions/          # Train/Dev/Test splits (Persian questions + Gold SQL)
│   ├── golden_sql/         # Reference SQL for evaluation
│   └── audit/              # Phase 0 validation artifacts
├── results/
│   ├── benchmark/          # Timestamped research artifacts (Agent/Retrieval runs, Bootstrap CI)
│   └── error_analysis/     # Detailed error taxonomy, failure traces, and Ablation Matrix
├── src/
│   ├── config/             # Path registry and global SETTINGS
│   ├── graph/              # LangGraph orchestration (Nodes, Routes, State)
│   ├── nlu/                # Persian normalization and intent routing
│   ├── reflexion/          # Advanced SQL Critic, Planner, and Error Taxonomy
│   ├── sql_validation/     # Syntax and safety validators
│   ├── generation/         # Local LLM (LlamaCpp) and prompt templates
│   ├── retrieval/          # Hybrid CAG/RAG (BM25 + ChromaDB)
│   └── evaluation/         # Metrics, Scorer, Benchmark Runner, and LLM-as-a-Judge
└── scripts/                # High-level entry points (run_agent, run_benchmark)
```

## مسیرهای مهم برای Phase 10

برای benchmark و ادامه توسعه پژوهشی، نقش پوشه‌ها این است:

- `scripts/run_benchmark.py`: دستور اصلی ترمینال برای اجرای `retrieval`, `gold`, `agent` و بعداً `--use-judge`.
- `benchmark/configs/`: configهای قابل بازتولید برای مدل‌ها، prompt policy، retrieval policy و ablation id.
- `experiments/configs/`: configهای ablation مثل A0 تا A7/A10 که باید فقط یک متغیر را تغییر دهند.
- `src/evaluation/`: sampling، metric، bootstrap CI، reliability، error taxonomy، judge و report generator.
- `src/graph/`: state و nodeهایی که prompt، response، SQL attempt، validation و execution trace را تولید می‌کنند.
- `results/benchmark/`: خروجی timestamped هر run. اسم فولدر باید شامل mode، dataset، model slug و config/ablation id باشد.
- `results/error_analysis/`: گزارش‌های failure، taxonomy و representative examples.
- `results/reports/`: خروجی‌های نهایی paper-ready بعد از اینکه benchmark و ablation تثبیت شدند.

Artifact استاندارد هر benchmark باید حداقل شامل این‌ها باشد:

```text
results/benchmark/<timestamp>_<mode>_<dataset>_<model_slug>_<ablation_id>/
  <prefix>_config.json
  <prefix>_predictions.jsonl
  <prefix>_attempts.jsonl
  <prefix>_failures.jsonl
  <prefix>_summary.json
  <prefix>_summary.md
  <prefix>_benchmark_results.csv
  <prefix>_reliability_summary.csv
  <prefix>_error_taxonomy.csv
  <prefix>_paper_tables.md
```

اگر LLM-as-a-Judge فعال باشد، این فایل‌ها هم اضافه می‌شوند:

```text
  <prefix>_judgments.jsonl
  <prefix>_judge_reasoning.md
  <prefix>_judge_costs.json
  <prefix>_semantic_business_summary.csv
```

## تفکیک مسئولیت تست‌ها

- اجرای SQL و مقایسه result با gold SQL در Phase 10 و `src/evaluation/metrics.py` سنجیده می‌شود.
- درست بودن مفهومی/بیزینسی SQL نسبت به سؤال، metric جدا دارد و در Phase 16 با `src/evaluation/llm_judge.py` یا static semantic checks سنجیده می‌شود.
- behavioral examples با `expected_action` سنجیده می‌شوند و نباید وارد EX شوند.
- safety و unsafe pass-through باید همیشه جدا گزارش شوند و target آن `0` است.

## اصل طراحی آموزشی

این پروژه را مثل یک pipeline شبیه compiler بخوانید:

```text
Persian question
  -> normalization / intent / safety / ambiguity
  -> QIR and schema/value linking
  -> compact CAG context
  -> local LLM candidate SQL
  -> deterministic validation and repair
  -> read-only execution
  -> reliability-aware output
  -> benchmark trace and error analysis
```

## منبع‌های تصمیم‌گیری

- ساختار پوشه‌ها: `docs/08_PROJECT_STRUCTURE_AND_FILE_MAP.md`
- dataset و فایل‌های ارزیابی: `docs/09_DATASET_AND_EVALUATION_FILES_GUIDE.md`
- ترتیب build و gateها: `docs/07_IMPLEMENTATION_ROADMAP_AND_REQUIREMENTS.md`
- validation/reflexion/safe execution: `docs/05_SQL_GENERATION_VALIDATION_REFLEXION.md`
- evaluation و ablation: `docs/06_EVALUATION_ABLATION_AND_PAPER_PLAN.md`
- وضعیت taskهای فعلی: `task.md`
- نقشه اجرایی جدید: `DEVELOPMENT_ROADMAP.md`
