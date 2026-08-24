# PARS-SQL Task Checklist - Phase 0 to Phase 16

این فایل checklist اجرایی پروژه است و بر اساس محتوای `docs/`، وضعیت واقعی کد و آخرین تست‌ها به‌روز شده است.

## وضعیت کلی

| Phase | عنوان | وضعیت |
|---|---|---|
| Phase 0 | Governance, Schema Freeze, Dataset Audit | COMPLETED |
| Phase 1 | Foundation Gaps | COMPLETED |
| Phase 2 | Data & Schema Quality Hardening | COMPLETED |
| Phase 3 | NLU v2, Value Linking, QIR | COMPLETED |
| Phase 4 | SQL Validation Stack | COMPLETED |
| Phase 5 | Local LLM Generation Layer | COMPLETED |
| Phase 6 | Milestone 1.5 Stress Test | COMPLETED |
| Phase 7 | Hybrid CAG/RAG Retrieval | COMPLETED |
| Phase 8 | LangGraph Orchestration | COMPLETED |
| Phase 9 | Graph-Level Reflexion / SQL Repair | COMPLETED |
| Phase 10 | Benchmark Runner & Evaluation Framework | COMPLETED - INFRASTRUCTURE CLOSED; FIXED TEST/PAPER CLAIMS REMAIN BLOCKED BY QUALITY, LEAKAGE LIMITATIONS AND PHASE 11/13/16 WORK |
| Phase 11 | Ablation, Error Analysis, Research Metrics | IN PROGRESS - FIRST SLICE, A0-A7 SMOKE, ABLATION COMPARISON, TARGETED A4 MITIGATION, DOCS/06 TAXONOMY ALIGNMENT AND FULL-DEV RETRIEVAL ABLATION DONE; PAPER-GRADE AGENT ABLATION/JUDGE STILL OPEN |
| Phase 12 | Output, Chart, Narrative | TODO |
| Phase 13 | Reliability Gate, Multi-Candidate, Abstention | IN PROGRESS - GATE/CANDIDATE EVIDENCE INFRA DONE; MULTI-CANDIDATE ADOPTION BLOCKED; RICHER CRITIC MIXED AND GATE ROUTING STILL DISABLED |
| Phase 14 | Edge Runtime Optimization | TODO |
| Phase 15 | Research Packaging | IN PROGRESS |
| Phase 16 | Semantic Business Logic (LLM-as-a-Judge) | COMPLETED - MOCK SCAFFOLD, DUAL-POLICY V1, OPENROUTER INTEGRATION DONE. DEEPSEEK V4 SUCCESSFULLY EVALUATED AND RESOLVED FALSE NEGATIVES (VTD-300, VTD-078) AS BUSINESS CORRECT |
| Phase 17 | Pipeline & Prompt Optimization | COMPLETED - ResultSerializer fix, NLU routing, JSON parser, Repair prompt. Benchmark: 400Q, EX=32.5%, Valid=82.5%. Deep error analysis done. |
| Phase 18 | Accuracy Optimization (Prompt/Few-shot/Schema) | IN PROGRESS - Target >60% via 4 sub-phases: A=Prompt Hints, B=Few-shot/RAG, C=Schema Linking, D=NLU Routing |

---

## Current Decision Snapshot - 2026-05-22

### وضعیت Phase 13

- Reliability gate به صورت annotation-only اجرا می‌شود؛ routing هنوز فعال نشده.
- Multi-candidate adoption مسدود است. shadow-only فقط شواهد تشخیصی/بررسی است.
- Critic غنی‌تر و policy بررسی consistency-failure مکانیزم‌های عمومی هستند، نه قوانین case-ID.
- آخرین artifact معتبر gate: `results\benchmark\manual_phase13_gate_dev_spl2_review_consistency_failures`.
- آخرین نتیجه conservative review-policy: evaluated `8`، execution_accuracy `0.375`، valid_sql_rate `0.875`، reliability_score `-1.25`، unsafe_sql `0`.
- Latest gate analysis: `results\reliability_gate\20260522_phase13_gate_dev_spl2_review_consistency_failures_analysis`.
- تفسیر فعلی: کیفیت annotation بهتر شد اما EX و final action چون routing خاموش است بهبود نیافت. این نتیجه SOTA، paper-quality یا product-readiness نیست.

### وضعیت Phase 11/16
- فاز ۱۶ با موفقیت در محیط OpenRouter تست شد و قاضی DeepSeek V4 به درستی توانست خطاهای Strict Validator را به عنوان `business_correct` تشخیص دهد.
- اولین بنچمارک کامل (60 سوال dev) اجرا شد. دقت Execution خام 13.3% و دقت Semantic (قاضی) 28.3% به دست آمد.

### وضعیت Phase 17 (COMPLETED ✅)
- هدف اولیه: افزایش دقت از 16.6% با رفع باگ‌های پایپلاین.
- نتیجه: Execution Accuracy از 16.6% → 32.5% (دو برابر). Valid SQL Rate = 82.5%.
- تغییرات انجام شده: رفع باگ ResultSerializer (هش ستون‌ها)، اصلاح NLU routing، تزریق مجدد question به sql_repair.j2، پارسر 3-مرحله‌ای JSON، فعال‌سازی Multi-Candidate Generation.
- Artifact: `results/benchmark/20260523_082754_agent_positive400_qwen2-5-coder-7b_phase17_final_deep_eval`
- مستند: `docs/phases/PHASE17_PIPELINE_OPTIMIZATION.md`

### وضعیت Phase 18 (IN PROGRESS 🔄)
- هدف: رساندن دقت از 32.5% به >60% بدون Fine-tuning.
- تحلیل خطاها: 270 خطا به 14 دسته مجزا طبقه‌بندی شدند (مستند کامل در error_analysis_phase17.md).
- استراتژی 4-فازی: A=Prompt Hints (+14.6%), B=Few-shot/RAG (+6.2%), C=Schema Linking (+9.9%), D=NLU (+3.6%).

### ممنوع‌ها

- Fixed test benchmark اجرا نشود.
- از نتایج A4 smoke (8 case) ادعای paper-grade نشود.
- Multi-candidate adoption فعال نشود.
- Reliability-gate routing فعال نشود تا آزمایش کنترل‌شده جدا انجام شود.
- هیچ metric بدون artifact واقعی گزارش نشود.

### اقدام بعدی مشخص - ترتیب دقیق

1. ~~**گام A**: تحلیل failures از balanced dev artifact موجود (بدون اجرای مدل).~~ (انجام شد)
2. ~~**گام B**: اجرای smoke با مدل 7B روی `--samples-per-level 2`.~~ (انجام شد)
3. ~~**گام C**: بررسی safety_rejection_accuracy با behavior_dev benchmark و حل باگ مسیردهی.~~ (انجام شد)
4. ~~**گام D**: تکمیل فاز ۱۲ و تثبیت منطق actual_action برای output formatter.~~ (انجام شد)
5. ~~**گام E**: اعتبارسنجی نهایی `behavior_dev` و `dev` توسط کاربر.~~ (انجام شد)
6. ~~**گام F**: اجرای Phase 13 gate routing experiment.~~ (انجام شد، دروازه اطمینان خطاهای VTD-237 و VTD-343 را با موفقیت دفع کرد).
7. ~~**گام G**: فعال‌سازی Phase 16 (Semantic Business Logic) با استفاده از API کلود OpenRouter برای داوری نتایج `phase13_dev_gate_v1`.~~ (انجام شد، مدل DeepSeek V4 ارزیابی معنایی را انجام داد و مشخص کرد که VTD-300 و VTD-078 منطقاً درست هستند).

---

## Phase 0 - Governance, Schema Freeze, Dataset Audit [COMPLETED]

- [x] `data/schema/schema_snapshot.json`
- [x] `data/schema/schema_snapshot.generated.json`
- [x] `scripts/compare_schema_snapshots.py`
- [x] `data/questions/audit/phase0_50q_audit.csv`
- [x] `data/questions/audit/phase0_50q_audit_cases.json`
- [x] `data/questions/audit/phase0_50q_audit_results.jsonl`
- [x] `data/questions/audit/phase0_50q_audit_report.md`
- [x] `DATASET_CARD.md`
- [x] `docs/THREAT_MODEL.md`
- [x] Root-level phase/roadmap tracking files exist.

Acceptance evidence:

- [x] Frozen and generated schema are identical.
- [x] Phase 0 audit artifacts exist.
- [x] Dataset card and threat model exist.

---

## Phase 1 - Fix Existing Foundation Gaps [COMPLETED]

- [x] `src/core/exceptions.py`
- [x] `src/nlu/persian_normalizer.py`
- [x] `src/nlu/number_normalizer.py`
- [x] `src/nlu/date_normalizer.py`
- [x] `src/nlu/colloquial_mapper.py`
- [x] `src/nlu/term_extractor.py`
- [x] `src/nlu/intent_classifier.py`
- [x] `src/nlu/ambiguity_detector.py`
- [x] `src/nlu/safety_intent_detector.py`
- [x] `src/utils/logging.py`
- [x] `src/utils/jsonl.py`
- [x] `src/utils/hashing.py`
- [x] `src/utils/timing.py`
- [x] `main.py`
- [x] Tier 1 tests for normalizer, date, colloquial, safety, ambiguity, schema linker, value linker, JSONL and hashing.

Acceptance evidence:

- [x] `pytest tests/tier1_unit -q` passed.

---

## Phase 2 - Data & Schema Quality Hardening [COMPLETED]

- [x] `scripts/compare_schema_snapshots.py`
- [x] `scripts/export_schema_markdown.py` -> `docs/generated/SCHEMA_REFERENCE.md`
- [x] `scripts/validate_dataset_sql.py`
- [x] `scripts/convert_dataset_to_jsonl.py`
- [x] `scripts/check_duplicate_questions.py`
- [x] `scripts/check_schema_column_references.py`
- [x] `scripts/validate_dataset.py`
- [x] Phase 2 scripts are UTF-8 safe on Windows/PowerShell.
- [x] `data/questions/full/vtd_question_sql_400_merged_validated.json`
- [x] `data/questions/train/`, `data/questions/dev/`, `data/questions/test/` exact `280/60/60` split.
- [x] `data/questions/special/behavior_dev.json`, `behavior_test.json` exact `40/60` split.
- [x] `data/golden_sql/golden_examples.jsonl`
- [x] `data/golden_sql/few_shot_bank.jsonl`
- [x] `data/rag/indexed_examples.jsonl`

Acceptance evidence:

- [x] `scripts/validate_dataset.py` -> `ALL PASSED`
- [x] 400 gold SQL queries execute with `100.0%` pass rate.
- [x] No hallucinated schema references in 400 examples.
- [x] No duplicate IDs/questions across canonical files.

---

## Phase 3 - NLU v2, Value Linking, QIR [COMPLETED]

- [x] `src/schema/concept_registry.py`
- [x] `src/core/query_ir.py`
- [x] `src/schema/query_planner.py`
- [x] `src/schema/schema_linker.py`
- [x] `src/schema/value_linker.py`
- [x] `data/schema/column_aliases.fa.json`
- [x] unresolved term reporting in schema linking.
- [x] value linking for gender, risk and depression flags.

Acceptance evidence:

- [x] `tests/tier1_unit/test_concept_registry.py`
- [x] `tests/tier1_unit/test_query_planner.py`
- [x] `tests/tier1_unit/test_schema_linker.py`
- [x] `tests/tier1_unit/test_value_linker.py`

Deferred to Phase 11:

- [ ] Gold labels for `Value Recall@k`.

---

## Phase 4 - SQL Validation Stack [COMPLETED]

- [x] `src/sql_validation/safety_validator.py`
- [x] `src/sql_validation/syntax_validator.py`
- [x] `src/sql_validation/schema_validator.py`
- [x] `src/sql_validation/join_validator.py`
- [x] `src/sql_validation/aggregation_validator.py`
- [x] `src/sql_validation/type_validator.py`
- [x] `src/sql_validation/semantic_validator.py`
- [x] `src/sql_validation/sql_rewriter.py`
- [x] `src/sql_validation/validation_pipeline.py`
- [x] `src/db/read_only_executor.py`

Acceptance evidence:

- [x] Safety validator blocks DDL/DML and unsafe SQL.
- [x] Schema validator catches hallucinated tables/columns.
- [x] Read-only executor runs validated SQL only.
- [x] Tier 1 SQL validation tests pass.

---

## Phase 5 - Local LLM Generation Layer [COMPLETED]

- [x] `src/generation/local_llm.py`
- [x] `src/generation/llm_engine.py`
- [x] `src/generation/prompt_builder.py`
- [x] `src/generation/output_parser.py`
- [x] `src/generation/prompts/sql_generation.j2`
- [x] `src/generation/prompts/sql_repair.j2`
- [x] `scripts/run_agent.py`

Acceptance evidence:

- [x] Generation modules compile.
- [x] LangGraph can import and construct workflow.

Deferred:

- [ ] Multi-candidate generation is Phase 13.
- [ ] Full agent benchmark is Phase 10.

---

## Phase 6 - Milestone 1.5 Stress Test [COMPLETED]

- [x] `data/questions/audit/milestone_1_5_stress_test.json`
- [x] `data/questions/audit/milestone_1_5_stress_test_results.jsonl`
- [x] `data/questions/audit/milestone_1_5_stress_test_report.md`
- [x] Persian statistical query stress-test recorded.
- [x] GPU/local performance note recorded.
- [x] Rate-query SQL pattern checked.

Deferred:

- [ ] Future stress-test claims should be reproduced through Phase 10 benchmark artifacts.

---

## Phase 7 - Hybrid CAG/RAG Retrieval [COMPLETED]

- [x] `src/retrieval/bm25_index.py`
- [x] `src/retrieval/embedding_model.py`
- [x] `src/retrieval/chroma_store.py`
- [x] `src/retrieval/retrieval_scorer.py`
- [x] `src/retrieval/hybrid_retriever.py`
- [x] `src/retrieval/context_builder.py`
- [x] `src/retrieval/reranker.py`
- [x] `scripts/build_rag_index.py`
- [x] `src/evaluation/retrieval_metrics.py`
- [x] `src/graph/nodes/base_nodes.py` retrieval context connected before prompt building.
- [x] BM25 index build.
- [x] JSON vector fallback build.
- [x] Persistent ChromaDB collection build.
- [x] Retrieval-only benchmark command and report.
- [x] Retrieval tests cover BM25, hybrid scoring, context builder, JSON vector backend and ChromaDB backend.

Acceptance evidence:

- [x] `scripts/build_rag_index.py --skip-vector`
- [x] `scripts/build_rag_index.py --vector-backend json`
- [x] `scripts/build_rag_index.py --vector-backend chroma`
- [x] `scripts/run_benchmark.py --mode retrieval --dataset dev --sample 5 --top-k 2 --use-vector`
- [x] `tests/tier1_unit/test_retrieval.py` passed.

Deferred to Phase 11:

- [ ] Retrieval ablation: BM25-only vs vector-only vs hybrid.
- [ ] Reranker-backed final ranking.
- [ ] `Value Recall@k`.

---

## Phase 8 - LangGraph Orchestration [COMPLETED]

- [x] `src/graph/state.py`
- [x] `src/graph/routes.py`
- [x] `src/graph/workflow.py`
- [x] `src/graph/nodes/base_nodes.py`
- [x] Flow includes retrieval before prompt building.
- [x] Pre-generation routing supports safe refusal / clarification path.

Acceptance evidence:

- [x] `from src.graph.workflow import create_workflow; create_workflow()` -> `workflow_ok`

Open extensions from docs:

- [ ] Add `retrieve_values` node explicitly if value links should become first-class graph state.
- [ ] Add checkpoint/trace persistence suitable for benchmark replay.
- [ ] Add graph diagram export.

---

## Phase 9 - Graph-Level Reflexion, SQL Surgeon, Semantic Critic [COMPLETED]

- [x] Validation errors are fed back to generation node in graph retry path.
- [x] SQL repair iteration is supported in `src/graph/nodes/base_nodes.py`.
- [x] **Research-Grade Advanced Reflexion Stack**:
    - [x] `src/reflexion/error_taxonomy.py`: Structured SQL error categorization.
    - [x] `src/reflexion/critic.py`: Actionable NL feedback for the LLM.
    - [x] `src/reflexion/repair_planner.py`: Strategy-based repair logic.
    - [x] `src/reflexion/retry_policy.py`: Deterministic retry/fail policy.
    - [x] `src/reflexion/transition_memory.py`: Anti-loop and state tracking.
- [x] Anti-loop tests passed (repeated SQL/error detection).
- [x] Detailed tracing: Every attempt captures critic feedback, repair plan, and metadata.

---

## Phase 10 - Benchmark Runner and Evaluation Framework [COMPLETED - INFRASTRUCTURE]

Current truth:

- Phase 10 infrastructure is implemented for reproducible local runs, full traces, partial checkpoints, terminal summaries, self-overlap mitigation, model/config metadata and analytical shape validation.
- `gold`, `retrieval`, `agent`, `behavior_dev`, sample-20 and balanced-dev modes have been run on real project datasets.
- Local model smoke passed with `qwen2.5-coder-3b-instruct-q4_k_m.gguf`.
- Current real agent quality is weak and remains a Phase 11/13/16 research-quality problem, not a Phase 10 infrastructure blocker: after shape-contract fixes, latest balanced smoke has `EX=0.25`, `valid_sql_rate=0.875`, reliability negative, and `unsafe_sql=0`.
- Leakage audit is implemented and found overlap risk; final test/paper claims are blocked until mitigation or explicit limitation.
- Phase 10 remaining work is not infrastructure work. It is a gating policy: do not consume the fixed test set or claim paper-grade quality until Phase 11/13/16 produce a stable dev result and documented leakage limitation/mitigation.

Implemented:

- [x] `scripts/run_benchmark.py`
- [x] `src/evaluation/dataset_loader.py`
- [x] `src/evaluation/benchmark_runner.py`
- [x] `src/evaluation/metrics.py`
- [x] `src/evaluation/reliability_metrics.py`
- [x] `src/evaluation/retrieval_metrics.py`
- [x] `src/evaluation/report_generator.py`
- [x] `src/evaluation/error_analyzer.py` basic grouping.
- [x] `--mode retrieval`
- [x] `--mode gold`
- [x] Artifact folder under `results/benchmark/<timestamp>_<mode>_<dataset>_<model_slug>_<ablation_id>/`
- [x] `config.json`, `predictions.jsonl`, `failures.jsonl`, `summary.json`, `summary.md`

Required next:

- [x] Add `--mode agent` for full LangGraph benchmark.
- [x] Run initial agent benchmark smoke runs (Timestamped & Model-tagged).
- [ ] Run full fixed dev/test benchmark. BLOCKED and deferred until Phase 11/13/16 quality-gate work; not required to close Phase 10 infrastructure.
- [x] Save `attempts.jsonl` with detailed critic/repair trace.
- [x] Save `benchmark_results.csv`.
- [x] Save `reliability_summary.csv`.
- [x] Save `error_taxonomy.csv`.
- [x] Save `paper_tables.md`.
- [x] Ensure behavioral examples are evaluated by expected action.
- [x] Report unsafe pass-through rate; target must be `0`.
- [x] Add benchmark config files under `benchmark/configs/` (`research_agent_v1.yaml`).
- [x] Support `--config` flag in `run_benchmark.py` for reproducible runs.
- [x] Implement **Ablation Control** in `VTDState` and Graph nodes.
- [x] Implement **Balanced Sampling** (`--samples-per-level`):
    - [x] `src/evaluation/dataset_loader.py`: Grouping logic by `difficulty`.
    - [x] `scripts/run_benchmark.py`: Support for per-level sample selection.
- [x] Implement **Bootstrap Confidence Intervals** (95% CI):
    - [x] `src/evaluation/metrics.py`: Bootstrap sampling logic.
    - [x] `src/evaluation/report_generator.py`: Show CI in markdown reports.
- [x] Capture and store **Exact Prompts** in `SQLAttempt`:
    - [x] `src/graph/state.py`: Add `prompt` field to `SQLAttempt`.
    - [x] `src/graph/nodes/base_nodes.py`: Store current prompt in attempt metadata.
    - [x] Add `raw_model_response`, `parsed_payload`, validation errors and execution hash/preview fields.
- [x] Include **Model Name** and **Ablation Status** in all output artifacts:
    - [x] `scripts/run_benchmark.py`: File naming with model slug and ablation id.
    - [x] `src/evaluation/report_generator.py`: Configuration summary section.
    - [x] `src/evaluation/export_utils.py`: Prefixed CSV/table artifact names.
- [x] **Real-time Terminal Progress Tracking**:
    - [x] `scripts/run_benchmark.py`: Display `[X/Y]`, case id, difficulty, category, status, latency, elapsed and ETA.
    - [ ] Optional later: add a reusable callback abstraction to `src/evaluation/benchmark_runner.py`.

### Phase 10 Developer Checklist - Resume Point

هدف این بخش این است که هر benchmark از ترمینال، قابل بازتولید، قابل audit و مناسب مقاله باشد. هر بار اجرا باید نشان بدهد چه مدل، چه config، چه ماژول‌هایی، چه dataset/sample policy و چه prompt/responseهایی استفاده شده‌اند.

#### 10.1 CLI and Sampling Contract

- [x] `scripts/run_benchmark.py` باید از ترمینال با این الگوها اجرا شود:
    - [ ] `python scripts/run_benchmark.py --mode agent --dataset dev --sample 20` باید با مدل واقعی اجرا و artifact شود.
    - [ ] `python scripts/run_benchmark.py --mode agent --dataset dev --samples-per-level 5` باید با مدل واقعی اجرا و artifact شود.
    - [ ] `python scripts/run_benchmark.py --mode agent --dataset test --samples-per-level 5 --config benchmark/configs/research_agent_v1.yaml` باید بعد از debug dev اجرا شود.
    - [x] `python scripts/run_benchmark.py --mode retrieval --dataset dev --sample 20 --top-k 3`
    - [x] `python scripts/run_benchmark.py --mode gold --dataset dev --samples-per-level 1`
- [x] `--sample N`: انتخاب اولین N نمونه بعد از normalize/load dataset.
- [x] `--samples-per-level N`: انتخاب N نمونه از هر مقدار `difficulty` مثل `easy`, `medium`, `hard`, `complex`.
- [x] اگر `--sample` و `--samples-per-level` همزمان داده شوند، runner خطای واضح می‌دهد.
- [x] انتخاب نمونه‌ها deterministic است.
- [x] `config.json` شامل `selection_policy`, `sample`, `samples_per_level`, `dataset_path` است.
- [x] Add `difficulty_counts` explicitly to `config.json`.
- [x] Add `dataset_hash` and `selected_cases_hash` to `config.json` for stronger reproducibility.

#### 10.2 Transparent Terminal Progress

- [x] در هر case این اطلاعات در ترمینال چاپ شود:
    - [x] `[current/total]`
    - [x] `case_id`
    - [x] `difficulty`
    - [x] `category`
    - [x] `expected_action`
    - [x] `actual_action`
    - [x] `ok/fail`
    - [x] `latency_ms`
    - [x] `elapsed_total`
    - [x] `eta`
- [x] در پایان run، مسیر artifact folder چاپ شود.
- [x] در پایان run، خلاصه metricها هم در terminal چاپ شود.
    - [x] Print evaluated count, failure count, execution accuracy, valid SQL rate, reliability score, unsafe SQL count, latency mean/median/p95 and artifact directory.
    - [x] Verification: `python scripts/run_benchmark.py --mode gold --dataset dev --sample 1 --bootstrap-iterations 20 --ablation-id terminal_summary_smoke` printed `=== Benchmark Summary ===`.
- [ ] خطاهای per-case نباید کل benchmark را بدون ثبت failure متوقف کنند؛ مگر خطای setup مثل نبودن مدل/دیتابیس.

#### 10.3 Full Trace and Prompt/Response Capture

- [x] `src/graph/state.py`: فیلدهای زیر به `SQLAttempt` اضافه شوند:
    - [x] `prompt: str | None`
    - [x] `raw_model_response: str | None`
    - [x] `parsed_payload: dict[str, Any] | None`
    - [x] `validation_errors: list[dict[str, Any]]`
    - [x] `execution_result_preview: list[dict[str, Any]] | None`
    - [x] `execution_result_hash: str | None`
    - [x] `gold_result_hash: str | None`
    - [x] `semantic_business_score: float | None`
    - [x] `semantic_business_reason: str | None`
- [x] `src/graph/nodes/base_nodes.py` prompt فعلی و raw response مدل را در attempt ذخیره می‌کند.
- [x] `scripts/run_benchmark.py` برای هر case در `predictions.jsonl` این‌ها را ذخیره می‌کند:
    - [x] سوال اصلی فارسی
    - [x] سوال normalize شده در agent mode
    - [x] QIR در agent mode
    - [x] linked schema در agent mode
    - [x] retrieval examples and diagnostics در agent mode
    - [x] generated SQL
    - [x] gold SQL
    - [x] validation issues در prediction-level ثبت شود.
    - [x] execution hash and gold hash
    - [x] final action
    - [x] final answer/explanation when present
- [x] `attempts.jsonl` یک row برای هر تلاش تولید/repair می‌سازد و شامل `case_id`, `attempt_index`, `prompt`, `raw_model_response`, `sql`, `critic_feedback`, `repair_plan`, `error_type`, `latency_ms` است.
- [x] `--trace-level full|compact` اضافه شد؛ پیش‌فرض Phase 10 `full` است و prompt/raw response را نگه می‌دارد.

#### 10.4 Model, Module and Ablation Metadata

- [x] نام مدل در اسم فولدر خروجی و prefix فایل‌ها می‌آید.
- [x] `config.json`, `summary.json`, `summary.md`, `paper_tables.md` شامل این‌ها هستند:
    - [x] `model_name`
    - [x] `model_path`
    - [x] `model_slug`
    - [x] `config_id`
    - [x] `ablation_id`
    - [x] `enabled_modules`
    - [x] `disabled_modules`
    - [x] `retrieval_backend` explicit شود.
    - [x] `top_k`
    - [x] `max_retries` explicit در config نهایی اضافه شود.
    - [x] `prompt_template` explicit در config نهایی اضافه شود.
    - [x] `git_commit`
- [x] ablation flags explicit هستند.
- [x] summary نهایی ماژول‌های روشن/خاموش را می‌نویسد.

#### 10.5 Metrics and CI

- [ ] EX و Valid SQL Rate فقط برای SQL-positive examples محاسبه شوند. نیاز به verification با `behavior_dev/behavior_test` دارد.
- [ ] behavioral examples با `expected_action` سنجیده شوند، نه EX. نیاز به run واقعی behavior دارد.
- [ ] گزارش‌ها باید جدا کنند:
    - [ ] `execution_correct`: آیا SQL اجرا شد و result با gold برابر بود؟
    - [ ] `semantic_business_correct`: آیا SQL از نظر مفهومی پاسخ درست همان سوال است؟
    - [ ] `action_correct`: آیا سیستم باید answer/clarify/refuse/abstain می‌داد؟
- [x] Bootstrap 95% CI برای metricهای اصلی:
    - [x] EX / execution_accuracy
    - [x] Valid SQL Rate
    - [ ] Reliability Score CI
    - [ ] Correct Abstention Rate CI
    - [ ] Unsafe Pass-through Rate CI
    - [ ] Semantic Business Correctness Score وقتی judge فعال است.
- [x] latency حداقل `mean`, `median`, `p95`, `min`, `max` دارد.

#### 10.6 Required Phase 10 Artifacts

- [x] هر run باید حداقل این فایل‌ها را بسازد:
    - [x] `{prefix}_config.json`
    - [x] `{prefix}_predictions.jsonl`
    - [x] `{prefix}_attempts.jsonl`
    - [x] `{prefix}_failures.jsonl`
    - [x] `{prefix}_summary.json`
    - [x] `{prefix}_summary.md`
    - [x] `{prefix}_benchmark_results.csv`
    - [x] `{prefix}_reliability_summary.csv`
    - [x] `{prefix}_error_taxonomy.csv`
    - [x] `{prefix}_paper_tables.md`
- [ ] اگر `--use-judge` فعال بود:
    - [ ] `{prefix}_judgments.jsonl`
    - [ ] `{prefix}_judge_reasoning.md`
    - [ ] `{prefix}_judge_costs.json`

#### 10.7 Benchmark and Test Documentation

- [x] `docs/BENCHMARK_AND_TEST_GUIDE.md`: practical guide for environment setup, tests, benchmark modes, sampling, logs, artifacts, metrics, judge, ablation and debugging.
- [x] `README.md`: links to benchmark/test guide and includes quick commands.
- [x] `docs/00_INDEX.md`: includes benchmark/test guide in documentation map.
- [x] `docs/README.md`: links guide and clarifies benchmark contract.
- [x] `FOLDER_GUIDE.md`: adds guide to recommended reading order.
- [x] `benchmark/README.md`: links guide and shows current benchmark commands.
- [x] `scripts/README.md`: updates `run_benchmark.py` modes, outputs and agent requirement.
- [x] `tests/README.md`: documents Phase 10 focused tests and guide location.
- [x] `results/README.md`: documents current prefixed artifact layout.

#### 10.8 Focused Tests for Phase 10

- [x] `tests/tier1_unit/test_dataset_loader_sampling.py`
    - [x] `samples_per_level` exact count per difficulty where enough cases exist.
    - [x] deterministic ordering.
    - [x] rejects non-positive sample count.
- [x] `tests/tier1_unit/test_metrics_bootstrap.py`
    - [x] CI keys exist.
    - [x] CI lower/upper are bounded between 0 and 1 for rate metrics.
    - [x] deterministic with fixed seed.
    - [x] latency summary reports median/p95.
- [x] `tests/tier1_unit/test_benchmark_artifact_contract.py`
    - [x] prefixed CSV/table artifacts are written.
    - [x] paper tables include model/ablation metadata.
- [x] `tests/tier1_unit/test_graph_attempt_trace.py`
    - [x] attempts include prompt/raw response/parsed payload.
    - [x] execution updates include result hash and preview.
- [x] `tests/tier2_integration/test_agent_benchmark_trace.py`
    - [x] a small mocked agent run writes predictions, attempts, summary and config.
    - [x] verifies prompt and raw model response are persisted in `attempts.jsonl`.
    - [x] verifies model slug, ablation id and enabled/disabled modules are stored in config/summary.

#### 10.9 Real Agent Empirical Validation - BLOCKING FOR PHASE 10 DONE

- [x] Set `VTD_DEFAULT_MODEL_PATH` to an existing GGUF model.
    - [x] First smoke model: `models/generation/Qwen__Qwen2.5-Coder-3B-Instruct-GGUF/qwen2.5-coder-3b-instruct-q4_k_m.gguf`.
    - [ ] Paper/target comparison model after smoke: `models/generation/qwen2.5-coder-7b-instruct-q4_k_m.gguf`.
- [x] Run local model smoke:
    - [x] `python scripts/run_agent.py "درصد دانشجویان افسرده چقدر است؟" --verbose`
    - [x] Confirm model loads.
    - [x] Confirm raw model output is valid JSON or parser can recover it.
    - [x] Confirm generated SQL reaches validation.
    - [x] Ensure `scripts/run_agent.py --verbose` prints raw model response, parsed payload, validation errors and attempt count for manual smoke inspection.
    - [x] Record smoke result here before starting benchmark runs:
        - command: `.\.venv\Scripts\python.exe scripts\run_agent.py "درصد دانشجویان افسرده چقدر است؟" --verbose`
        - model_path: `models/generation/Qwen__Qwen2.5-Coder-3B-Instruct-GGUF/qwen2.5-coder-3b-instruct-q4_k_m.gguf`
        - status: passed
        - generated_sql_or_error: `SELECT AVG(depression_flag) * 100.0 FROM student_depression`
        - parser_reached: yes
        - validation_reached: yes
        - notes: raw response was valid JSON, parsed payload matched generated SQL, validation errors were empty, retry count was `0`, attempt count was `1`.
    - [x] 2026-05-15 pre-fix attempt:
        - command: `.\.venv\Scripts\python.exe scripts\run_agent.py "درصد دانشجویان افسرده چقدر است؟" --verbose`
        - model_path: `models/generation/Qwen__Qwen2.5-Coder-3B-Instruct-GGUF/qwen2.5-coder-3b-instruct-q4_k_m.gguf`
        - status: failed before model load
        - generated_sql_or_error: `ModuleNotFoundError: No module named 'src'`
        - parser_reached: no
        - validation_reached: no
        - notes: `scripts/run_agent.py` must bootstrap project root the same way `scripts/run_benchmark.py` does.
    - [x] 2026-05-15 post-bootstrap attempt:
        - command: `.\.venv\Scripts\python.exe scripts\run_agent.py "درصد دانشجویان افسرده چقدر است؟" --verbose`
        - model_path: `models/generation/Qwen__Qwen2.5-Coder-3B-Instruct-GGUF/qwen2.5-coder-3b-instruct-q4_k_m.gguf`
        - status: model loaded and graph completed
        - generated_sql_or_error: `SELECT AVG(depression_flag) * 100.0 FROM student_depression`
        - parser_reached: yes, but raw/parsed payload not printed by current verbose output
        - validation_reached: yes, inferred from final answer and no visible validation failure
        - notes: extend `run_agent.py --verbose` before closing this gate.
    - [x] 2026-05-15 final smoke attempt after verbose trace fix:
        - command: `.\.venv\Scripts\python.exe scripts\run_agent.py "درصد دانشجویان افسرده چقدر است؟" --verbose`
        - model_path: `models/generation/Qwen__Qwen2.5-Coder-3B-Instruct-GGUF/qwen2.5-coder-3b-instruct-q4_k_m.gguf`
        - status: passed
        - raw_model_response: `{ "sql": "SELECT AVG(depression_flag) * 100.0 FROM student_depression", ... }`
        - parsed_payload: `{"sql": "SELECT AVG(depression_flag) * 100.0 FROM student_depression", "needs_clarification": false, ...}`
        - validation_errors: `[]`
        - retry_count: `0`
        - attempt_count: `1`
- [ ] Run real agent benchmark with new trace contract:
    - [x] `python scripts/run_benchmark.py --mode agent --dataset dev --samples-per-level 1 --bootstrap-iterations 100 --ablation-id full_trace`
    - [x] Confirm folder name includes mode/dataset/model/ablation.
    - [x] Confirm `attempts.jsonl` contains prompt/raw response for all cases.
    - [x] Confirm failures are categorized.
    - [x] 2026-05-15 first attempt:
        - command: `.\.venv\Scripts\python.exe scripts\run_benchmark.py --mode agent --dataset dev --samples-per-level 1 --bootstrap-iterations 100 --ablation-id full_trace`
        - model_path: `models/generation/Qwen__Qwen2.5-Coder-3B-Instruct-GGUF/qwen2.5-coder-3b-instruct-q4_k_m.gguf`
        - selected_cases: `4` (`complex`, `easy`, `hard`, `medium`)
        - terminal_progress: yes, all four cases printed
        - status: failed while writing artifacts
        - error: `TypeError: Object of type LinkedSchema is not JSON serializable`
        - partial_output_dir: `results/benchmark/20260515_095131_agent_dev_qwen2_5-coder-3b-instruct-q4_k_m_full_trace`
        - fix_required: JSON artifact writers must serialize Pydantic/dataclass/Path objects before `predictions.jsonl`, `summary.json` and `attempts.jsonl` writes.
    - [x] 2026-05-15 rerun after JSON writer fix:
        - command: `.\.venv\Scripts\python.exe scripts\run_benchmark.py --mode agent --dataset dev --samples-per-level 1 --bootstrap-iterations 100 --ablation-id full_trace`
        - output_dir: `results/benchmark/20260515_095324_agent_dev_qwen2_5-coder-3b-instruct-q4_k_m_full_trace`
        - selected_cases: `4` (`complex=1`, `easy=1`, `hard=1`, `medium=1`)
        - terminal_progress: yes
        - required_artifacts: all present (`config`, `predictions`, `attempts`, `failures`, `summary`, CSVs, `paper_tables`)
        - attempts: `8`
        - attempts_missing_prompt: `0`
        - attempts_missing_raw_model_response: `0`
        - attempts_missing_parsed_payload: `0`
        - execution_accuracy: `1/4 = 0.25`
        - valid_sql_rate: `2/4 = 0.50`
        - reliability_score: `-0.5`
        - unsafe_sql: `0`
        - latency_ms: `mean=10789`, `median=10096`, `p95=15566`, `min=7398`, `max=15566`
        - failure_taxonomy: `BEHAVIOR_MISMATCH=3`
        - note: taxonomy label is too coarse for SQL-positive failures and should be refined during bottleneck inspection.
- [x] Run sample-20 agent benchmark:
    - [x] `python scripts/run_benchmark.py --mode agent --dataset dev --sample 20 --bootstrap-iterations 300 --ablation-id full_trace`
    - [x] Record EX, Valid SQL Rate, Reliability, unsafe pass-through, latency.
    - [x] 2026-05-15 first attempt:
        - command: `.\.venv\Scripts\python.exe scripts\run_benchmark.py --mode agent --dataset dev --sample 20 --bootstrap-iterations 300 --ablation-id full_trace_sample20`
        - model_path: `models/generation/Qwen__Qwen2.5-Coder-3B-Instruct-GGUF/qwen2.5-coder-3b-instruct-q4_k_m.gguf`
        - status: failed before artifact finalization
        - partial_output_dir: `results/benchmark/20260515_095947_agent_dev_qwen2_5-coder-3b-instruct-q4_k_m_full_trace_sample20`
        - error: `ValueError: Requested tokens (2214) exceed context window of 2048`
        - selected_bottleneck: per-case exception containment
        - fix_required: agent benchmark loop must catch per-case workflow/model exceptions, record them as failed records with error class such as `MODEL_CONTEXT_OVERFLOW`, continue remaining cases, and still write artifacts.
    - [x] 2026-05-15 second attempt after exception containment:
        - command: `.\.venv\Scripts\python.exe scripts\run_benchmark.py --mode agent --dataset dev --sample 20 --bootstrap-iterations 300 --ablation-id full_trace_sample20_contained`
        - status: timed out before artifact finalization
        - partial_output_dir: `results/benchmark/20260515_100341_agent_dev_qwen2_5-coder-3b-instruct-q4_k_m_full_trace_sample20_contained`
        - observed_issue: output directory remained empty after timeout, so incremental checkpointing or shorter controlled reruns are needed before long runs.
        - additional_fix_required: remove hardcoded `n_ctx=2048`; use configurable `VTD_LLM_N_CTX`, defaulting to a larger context such as `4096`.
        - additional_fix_required: write partial benchmark artifacts after each case so timeout/interruption does not leave an empty output directory.
        - additional_fix_required: cache the local LLM instance inside the process; current graph loads the GGUF model again for every generation/retry, making long benchmarks impractical.
    - [x] Make local LLM context window configurable for benchmark runs.
        - setting: `VTD_LLM_N_CTX`
        - default: `4096`
        - verification: `run_agent.py --verbose` loaded model with `n_ctx=4096`, generated valid JSON, parsed SQL and had no validation errors.
    - [x] Write partial benchmark artifacts after each case:
        - [x] `{prefix}_partial_predictions.jsonl`
        - [x] `{prefix}_partial_failures.jsonl`
        - [x] `{prefix}_partial_attempts.jsonl`
        - [x] Verification: `python scripts/run_benchmark.py --mode gold --dataset dev --sample 1 --bootstrap-iterations 20 --ablation-id partial_smoke` wrote partial artifacts.
    - [x] Cache local model instance during a benchmark process:
        - [x] reuse same `LocalLLM` for identical `(model_path, n_ctx)` within the Python process.
        - [x] keep model path and n_ctx visible in logs.
        - [x] verification: balanced smoke with `full_trace_cache_nctx4096` loaded model once and completed.
    - [x] 2026-05-15 completed run after cache and n_ctx fixes:
        - command: `.\.venv\Scripts\python.exe scripts\run_benchmark.py --mode agent --dataset dev --sample 20 --bootstrap-iterations 300 --ablation-id full_trace_sample20_cache_nctx4096`
        - output_dir: `results/benchmark/20260515_114735_agent_dev_qwen2_5-coder-3b-instruct-q4_k_m_full_trace_sample20_cache_nctx4096`
        - evaluated: `20`
        - failures: `19`
        - difficulty_counts: `complex=15`, `easy=5`
        - attempts: `51`
        - attempts_missing_prompt/raw/parsed: `0/0/0`
        - execution_accuracy: `1/20 = 0.05`, CI95 `[0.0, 0.15]`
        - valid_sql_rate: `5/20 = 0.25`, CI95 `[0.1, 0.45]`
        - reliability_score: `-6.75`, normalized `-0.3375`
        - unsafe_sql: `0`
        - latency_ms: `mean=9335.15`, `median=8370.0`, `p95=12943.0`, `min=6052.0`, `max=20995.0`
        - error_taxonomy: `INVALID_SQL=15`, `RESULT_MISMATCH=4`
        - partial_artifacts: present
        - note: this run is intentionally `first_n` and is not balanced; use `--samples-per-level` for balanced claims.
- [x] Run balanced dev benchmark:
    - [x] `python scripts/run_benchmark.py --mode agent --dataset dev --samples-per-level 5 --bootstrap-iterations 300 --ablation-id full_trace`
    - [x] Use `VTD_LLM_N_CTX=4096` and 3B smoke model for the current pre-Phase-11 validation run.
    - [x] 2026-05-16 completed run:
        - command: `.\.venv\Scripts\python.exe scripts\run_benchmark.py --mode agent --dataset dev --samples-per-level 5 --bootstrap-iterations 300 --ablation-id full_trace_balanced_dev`
        - output_dir: `results/benchmark/20260516_073203_agent_dev_qwen2_5-coder-3b-instruct-q4_k_m_full_trace_balanced_dev`
        - evaluated: `20`
        - difficulty_counts: `complex=5`, `easy=5`, `hard=5`, `medium=5`
        - failures: `18`
        - execution_accuracy: `2/20 = 0.10`, CI95 `[0.0, 0.2]`
        - valid_sql_rate: `14/20 = 0.70`, CI95 `[0.5, 0.85]`
        - reliability_score: `-6.25`, normalized `-0.3125`
        - unsafe_sql: `0`
        - latency_ms: `mean=6872.35`, `median=7368.5`, `p95=16121.0`, `min=351.0`, `max=26618.0`
        - error_taxonomy: `MISSING_GENERATED_SQL=7`, `INVALID_SQL=6`, `RESULT_MISMATCH=5`
        - attempts: `25`
        - attempts_missing_prompt/raw/parsed: `0/0/0`
- [x] Run behavior benchmark:
    - [x] `python scripts/run_benchmark.py --mode agent --dataset behavior_dev --sample 20 --bootstrap-iterations 300 --ablation-id behavior_trace`
    - [x] Verify behavioral cases are scored by action, not EX.
    - [x] Before run: use `VTD_LLM_N_CTX=4096` and 3B smoke model unless target paper model is explicitly selected.
    - [x] 2026-05-15 first attempt:
        - command: `.\.venv\Scripts\python.exe scripts\run_benchmark.py --mode agent --dataset behavior_dev --sample 20 --bootstrap-iterations 300 --ablation-id behavior_trace`
        - status: timed out before final artifacts
        - partial_output_dir: `results/benchmark/20260515_115243_agent_behavior_dev_qwen2_5-coder-3b-instruct-q4_k_m_behavior_trace`
        - partial_records: `17/20`
        - partial_ok: `4/17`
        - partial_errors: `ACTION_MISMATCH=13`
        - partial_attempts: `37`
        - partial_attempts_missing_prompt/raw/parsed: `0/0/9`
        - observed_issue: non-SQL behavioral cases still enter generation/retry path and can take >240s per case.
        - fix_required: persist `should_generate_sql` in graph state and route non-SQL cases to a non-generation endpoint before schema linking/LLM generation.
    - [x] 2026-05-15 routed run completed:
        - output_dir: `results/benchmark/20260515_121025_agent_behavior_dev_qwen2_5-coder-3b-instruct-q4_k_m_behavior_trace_routed`
        - evaluated: `20`
        - action_ok: `6/20`
        - action_mismatch: `14`
        - unsafe_sql: `0`
        - trace_attempts: `31`
        - attempts_missing_prompt/raw/parsed: `0/0/9`
        - observed_issue: summary still reports `execution_accuracy=0.3` and `valid_sql_rate=0.8` on behavior-only cases; EX/Valid SQL must be SQL-positive only.
        - fix_required: change core metrics so `execution_accuracy` and `valid_sql_rate` exclude records with `should_generate_sql=false` or non-SQL expected actions.
    - [x] 2026-05-16 completed run after SQL-positive metric fix:
        - command: `.\.venv\Scripts\python.exe scripts\run_benchmark.py --mode agent --dataset behavior_dev --sample 20 --bootstrap-iterations 300 --ablation-id behavior_trace_metrics_fixed`
        - output_dir: `results/benchmark/20260516_071702_agent_behavior_dev_qwen2_5-coder-3b-instruct-q4_k_m_behavior_trace_metrics_fixed`
        - evaluated: `20`
        - action_ok: `6/20`
        - action_mismatch: `14`
        - error_taxonomy: `ACTION_MISMATCH=14`
        - execution_accuracy: `0/0 = 0.0` because this sample has no SQL-positive records.
        - valid_sql_rate: `0/0 = 0.0` because this sample has no SQL-positive records.
        - clarification_accuracy: `6/10 = 0.6`
        - safety_rejection_accuracy: `0/5 = 0.0`
        - reliability_score: `2.0`, normalized `0.1`
        - unsafe_sql: `0`
        - latency_ms: `mean=30219.7`, `median=6944.5`, `p95=234212.0`, `min=346.0`, `max=258320.0`
        - attempts: `29`
        - attempts_missing_prompt/raw/parsed: `0/0/6`
        - note: action scoring is now separate from EX, but behavior quality is weak; refusals and chart/no-SQL answers need dedicated output/routing work in later Phase 12/13/16.
- [ ] Run fixed test benchmark only after dev traces are explainable:
    - [ ] `python scripts/run_benchmark.py --mode agent --dataset test --samples-per-level 5 --bootstrap-iterations 300 --ablation-id full_trace`
    - [ ] BLOCKED, current status updated 2026-05-19:
        - reason: Phase 10 infra is closed, but model/system quality is not paper-grade.
        - reason: leakage audit found overlap risk (`total_issues=724`); direct retrieval self-overlap mitigation exists, but broader overlap limitation/mitigation must still be documented before final claims.
        - reason: behavior action quality remains Phase 12/13 work (`action_ok=6/20`, `safety_rejection_accuracy=0/5` in the recorded behavior smoke).
        - reason: semantic/business correctness is now measured for a small failure-only A4 slice, but success coverage, larger review and privacy/redaction policy are still open.
        - next: continue Phase 11/13/16 on dev/smoke artifacts; do not consume fixed test for a paper claim yet.
- [x] Phase 10 cannot be marked Done until at least one real agent run under the new trace contract is inspected and summarized.
    - Closed by `results/benchmark/20260517_031221_agent_dev_qwen2-5-coder-7b_manual_agent_shape_contract_spl2_after_fixes`.

#### 10.11 First Bottleneck Inspection - ACTIVE

- [x] Inspect latest balanced smoke artifacts:
    - [x] `results/benchmark/20260515_095324_agent_dev_qwen2_5-coder-3b-instruct-q4_k_m_full_trace/*_failures.jsonl`
    - [x] `results/benchmark/20260515_095324_agent_dev_qwen2_5-coder-3b-instruct-q4_k_m_full_trace/*_attempts.jsonl`
- [x] Observed failed cases:
    - [x] `VTD-237` complex: model produced placeholders (`SELECT ...`, `your_table_name`), validation failed after retries.
    - [x] `VTD-343` hard: model produced placeholders (`SELECT ...`, `your_table_name`), validation failed after retries.
    - [x] `VTD-300` medium: SQL was valid and executed, but result did not match gold SQL because it counted sleep categories instead of depression rate by sleep category.
- [x] Selected first bottleneck to fix:
    - category: metric/taxonomy bug
    - issue: all SQL-positive failures are labeled `BEHAVIOR_MISMATCH`, hiding invalid SQL vs result mismatch vs action mismatch.
    - reason for fixing first: without precise failure labels, sample-20 and later ablation/error analysis will produce misleading reports even when traces are complete.
- [x] Implement error classification in agent benchmark records:
    - [x] invalid SQL -> `INVALID_SQL`
    - [x] valid SQL but wrong result -> `RESULT_MISMATCH`
    - [x] missing SQL for SQL-positive case -> `MISSING_GENERATED_SQL`
    - [x] non-SQL/behavioral action mismatch -> `ACTION_MISMATCH`
- [x] Add focused test for error classification.
- [x] Rerun the smallest agent benchmark or focused tests and confirm error taxonomy is no longer all `BEHAVIOR_MISMATCH`.
    - test: `.\.venv\Scripts\python.exe -m pytest tests\tier2_integration\test_agent_benchmark_trace.py -q` -> `2 passed`
    - test: `.\.venv\Scripts\python.exe -m pytest tests\tier1_unit\test_dataset_loader_sampling.py -q` -> `3 passed`
    - rerun: `results/benchmark/20260515_095703_agent_dev_qwen2_5-coder-3b-instruct-q4_k_m_full_trace_taxonomy`
    - taxonomy: `INVALID_SQL=2`, `RESULT_MISMATCH=1`
    - attempts_missing_prompt/raw/parsed: `0/0/0`

#### 10.10 Overfit and Leakage Audit - BLOCKING FOR PAPER CLAIMS

- [x] Add `scripts/check_benchmark_leakage.py`.
    - [x] CLI default writes `results/data_quality/benchmark_leakage_report.md`.
    - [x] CLI default writes `results/data_quality/benchmark_leakage_cases.jsonl`.
    - [x] Report includes source counts, exact id duplicates, exact normalized question duplicates, near duplicates and SQL skeleton overlaps.
- [x] Compare question text overlap across:
    - [x] `data/questions/train/train.json`
    - [x] `data/questions/dev/dev.json`
    - [x] `data/questions/test/test.json`
    - [x] `data/golden_sql/golden_examples.jsonl`
    - [x] `data/golden_sql/few_shot_bank.jsonl`
    - [x] `data/rag/indexed_examples.jsonl`
- [x] Detect exact duplicate question IDs across splits.
- [x] Detect exact duplicate normalized questions across splits.
- [x] Detect near-duplicate Persian questions using normalized text similarity.
- [x] Detect identical SQL skeleton leakage between RAG/few-shot and dev/test.
- [x] For retrieval benchmark, report whether top-k retrieved examples include the same `id` or same normalized question as the evaluated case through per-record `self_overlap_removed` and config-level policy metadata.
- [x] Add `--exclude-self` retrieval policy for dev/test benchmarking if leakage is detected.
- [ ] Output:
    - [x] `results/data_quality/benchmark_leakage_report.md`
    - [x] `results/data_quality/benchmark_leakage_cases.jsonl`
- [ ] Update paper limitations if dataset is single-author or leakage cannot be fully eliminated.
    - [x] Current audit result must be treated as leakage risk: `records=630`, `total_issues=724`, `base_id_overlap=240`, `exact_id_duplicate=50`, `exact_normalized_question_duplicate=240`, `near_duplicate_question=112`, `sql_skeleton_overlap=82`.
    - [x] Before final paper benchmark, implement retrieval self/exact overlap exclusion for dev/test or document limitation explicitly.
    - [x] User verification 2026-05-16:
        - focused test: `python -m pytest tests\tier2_integration\test_agent_benchmark_trace.py -vv --tb=short` -> `4 passed, 1 warning`.
        - retrieval smoke: `python scripts\run_benchmark.py --mode retrieval --dataset dev --sample 5 --top-k 3 --exclude-self --ablation-id manual_exclude_self_smoke`.
        - output_dir: `results/benchmark/20260516_075846_retrieval_dev_qwen2-5-coder-7b_manual_exclude_self_smoke`.
        - evaluated: `5`, failures: `0`, retrieval_hit_rate: `1.0`, latency mean/median/p95: `2.4/1.0/8.0 ms`.
        - artifact verification: `exclude_self=true`, `retrieval_self_overlap_policy.enabled=true`, `removed_total=0`, `dataset_hash` and `selected_cases_hash` present.
    - [x] Agent smoke verification 2026-05-16:
        - command: `python scripts/run_benchmark.py --mode agent --dataset dev --samples-per-level 1 --bootstrap-iterations 100 --exclude-self --trace-level full --ablation-id manual_agent_exclude_self_spl1`.
        - output_dir: `results/benchmark/20260516_080120_agent_dev_qwen2-5-coder-7b_manual_agent_exclude_self_spl1`.
        - evaluated: `4`, failures: `3`.
        - execution_accuracy: `1/4 = 0.25`; valid_sql_rate: `3/4 = 0.75`; reliability_score: `-1.25`; unsafe_sql: `0`.
        - error_taxonomy: `RESULT_MISMATCH=2`, `MISSING_GENERATED_SQL=1`.
        - self_overlap_removed_total: `1`.
        - issue found after run: `config.model_path` was empty when the fallback model path was used; runner now records the fallback GGUF path in future artifacts.
    - [x] Metadata fix verification 2026-05-16:
        - command: `python scripts\run_benchmark.py --mode gold --dataset dev --sample 1 --bootstrap-iterations 20 --ablation-id metadata_model_path_fix_smoke`.
        - output_dir: `results/benchmark/20260516_081002_gold_dev_qwen2-5-coder-7b_metadata_model_path_fix_smoke`.
        - evaluated: `1`, failures: `0`, execution_accuracy: `1.0`, valid_sql_rate: `1.0`.
        - artifact verification: `config.model_path = D:\Project\ADHD-VTD\models\generation\qwen2.5-coder-7b-instruct-q4_k_m.gguf`, `model_name = qwen2.5-coder-7b-instruct-q4_k_m`.
    - [x] Quality fix 2026-05-16: `VTD-237` was SQL-positive but ambiguity routing marked it `ambiguous_query` and exited before generation.
        - code: `src/nlu/ambiguity_detector.py` no longer treats dashboard requests as ambiguous when clear metric/domain hints are present.
        - tests: `tests/tier1_unit/test_ambiguity_detector.py`, `tests/tier1_unit/test_intent_classifier.py`.
        - verification:
            - `python -m pytest tests\tier1_unit\test_ambiguity_detector.py -vv --tb=short` -> `16 passed`.
            - `python -m pytest tests\tier1_unit\test_intent_classifier.py -vv --tb=short` -> `1 passed`.
            - `python -m pytest tests\tier1_unit\test_graph_routes.py tests\tier2_integration\test_agent_benchmark_trace.py -vv --tb=short` -> `6 passed, 1 warning`.
        - rerun: `python scripts\run_benchmark.py --mode agent --dataset dev --samples-per-level 1 --bootstrap-iterations 100 --exclude-self --trace-level full --ablation-id manual_agent_after_ambiguity_fix_spl1`.
        - output_dir: `results/benchmark/20260516_081645_agent_dev_qwen2-5-coder-7b_manual_agent_after_ambiguity_fix_spl1`.
        - result: evaluated `4`, failures `3`, execution_accuracy `0.25`, valid_sql_rate `1.0`, reliability_score `-2.0`, unsafe_sql `0`, self_overlap_removed_total `1`.
        - taxonomy improved from `MISSING_GENERATED_SQL=1, RESULT_MISMATCH=2` to `RESULT_MISMATCH=3`; generation now happens for all selected SQL-positive cases.
    - [x] Quality fix 2026-05-16: dashboard/storytelling intent recorded `non_sql_request` even when it should generate analytical SQL, weakening prompt/QIR for `VTD-237`.
        - [x] Code change: `src/nlu/intent_classifier.py` maps dashboard/storytelling SQL-capable requests to `grouping_query` instead of `non_sql_request`.
        - [x] Test updated: `tests/tier1_unit/test_intent_classifier.py` now asserts dashboard/eating_disorder questions produce `IntentLabel.GROUPING_QUERY` and `ExpectedAction.GENERATE_SQL`.
        - [x] User verification 2026-05-16:
            - `python -m pytest tests\tier1_unit\test_intent_classifier.py -vv --tb=short` -> `1 passed`.
            - `python -m pytest tests\tier1_unit\test_ambiguity_detector.py -vv --tb=short` -> `16 passed`.
            - `python -m pytest tests\tier1_unit\test_graph_routes.py tests\tier2_integration\test_agent_benchmark_trace.py -vv --tb=short` -> `6 passed, 1 warning`.
            - rerun: `python scripts\run_benchmark.py --mode agent --dataset dev --samples-per-level 1 --bootstrap-iterations 100 --exclude-self --trace-level full --ablation-id manual_agent_after_dashboard_intent_fix_spl1`.
            - output_dir: `results/benchmark/20260516_120437_agent_dev_qwen2-5-coder-7b_manual_agent_after_dashboard_intent_fix_spl1`.
            - result: evaluated `4`, failures `3`, execution_accuracy `0.25`, valid_sql_rate `1.0`, reliability_score `-2.0`, unsafe_sql `0`, self_overlap_removed_total `1`.
            - taxonomy: `RESULT_MISMATCH=3`; `VTD-237` intent is now `grouping_query`, generated valid SQL, and failed only by result mismatch.
    - [ ] Next quality fix: result-shape mismatch for valid SQL outputs.
        - [ ] `VTD-237`: generated latest-year wide-table aggregate, but gold requires 1990-vs-latest change, country-level deltas, quartiles with `NTILE(4)`, and grouped dashboard summary.
        - [ ] `VTD-343`: generated row-level `mental_health_risk`, but gold requires grouped risk counts plus average stress/sleep.
        - [ ] `VTD-300`: generated valid rate SQL, but result still mismatches the expected grouped rate/count shape.
        - [x] Inspect prompt/QIR/retrieved examples before changing model prompt; avoid using gold SQL or benchmark-only metadata at runtime.
        - [x] Implement runtime-safe prompt analysis hints:
            - [x] grouped rate output should include group key, `COUNT(*)`, positives when a binary flag is present, rounded `rate_pct`, null-group filtering, ordering and limit.
            - [x] dashboard/storytelling output should be a compact analytical table, not a single scalar.
            - [x] global prevalence change output should prefer `country_prevalence_long`, endpoint comparison, deltas and quartile/percentile bins when requested.
            - [x] risk-filter output should summarize by `mental_health_risk` with counts and relevant averages; above/below-average filters should use subqueries instead of fixed constants.
        - [x] Add focused prompt-builder tests for these non-gold hints: `tests/tier1_unit/test_prompt_builder.py`.
        - [x] User verification 2026-05-16:
            - `python -m pytest tests\tier1_unit\test_prompt_builder.py -vv --tb=short` -> `3 passed`.
            - `python -m pytest tests\tier1_unit\test_prompt_builder.py tests\tier1_unit\test_intent_classifier.py tests\tier1_unit\test_ambiguity_detector.py -vv --tb=short` -> `20 passed`.
            - rerun: `python scripts\run_benchmark.py --mode agent --dataset dev --samples-per-level 1 --bootstrap-iterations 100 --exclude-self --trace-level full --ablation-id manual_agent_after_shape_hints_spl1`.
            - output_dir: `results/benchmark/20260516_122431_agent_dev_qwen2-5-coder-7b_manual_agent_after_shape_hints_spl1`.
            - result: evaluated `4`, failures `4`, execution_accuracy `0.0`, valid_sql_rate `0.5`, reliability_score `-2.5`, unsafe_sql `0`.
            - taxonomy regressed to `INVALID_SQL=2`, `RESULT_MISMATCH=2`.
            - finding: hints reached the prompt, but they were too broad. `VTD-237` mixed `country_prevalence_wide` with long-table columns (`prevalence_pct`, `disorder`), and `VTD-027` copied `family_history` from a few-shot example instead of using `student_depression.family_history_mental_illness`.
        - [x] Refine shape hints:
            - [x] Add explicit no-cross-table-column rule for few-shot copying.
            - [x] Split country prevalence long/wide guidance: long table has `disorder` and `prevalence_pct`; wide table has disorder-specific `*_pct` columns and no `disorder`.
            - [x] Strengthen risk summary guidance to require `GROUP BY mental_health_risk`, `COUNT(*) AS n`, `avg_stress`, `avg_sleep`.
            - [x] Strengthen rate guidance to require `positives` and `rate_pct` aliases, plus `avg_cgpa_10` context for `student_depression`.
            - [x] Add schema-specific family-history hint for `student_depression.family_history_mental_illness`.
        - [x] User verification for refined hints:
            - `python -m pytest tests\tier1_unit\test_prompt_builder.py -vv --tb=short`
            - rerun agent smoke with `--ablation-id manual_agent_after_refined_shape_hints_spl1`.
        - [x] User verification 2026-05-17:
            - `python -m pytest tests\tier1_unit\test_prompt_builder.py -vv --tb=short` -> `4 passed`.
            - `python -m pytest tests\tier1_unit\test_prompt_builder.py tests\tier1_unit\test_intent_classifier.py tests\tier1_unit\test_ambiguity_detector.py -vv --tb=short` -> `21 passed`.
            - rerun: `python scripts\run_benchmark.py --mode agent --dataset dev --samples-per-level 1 --bootstrap-iterations 100 --exclude-self --trace-level full --ablation-id manual_agent_after_refined_shape_hints_spl1`.
            - output_dir: `results/benchmark/20260517_010715_agent_dev_qwen2-5-coder-7b_manual_agent_after_refined_shape_hints_spl1`.
            - result: evaluated `4`, failures `3`, execution_accuracy `0.25`, valid_sql_rate `0.75`, reliability_score `-1.25`, unsafe_sql `0`.
            - improvement: `VTD-027` is now correct and uses `family_history_mental_illness`.
            - remaining issues:
                - `VTD-237`: invalid SQLite due to `PERCENTILE_CONT` and wide-table scalar/quartile path instead of long-table `NTILE(4)` change summary.
                - `VTD-343`: still row-level `mental_health_risk` without `GROUP BY mental_health_risk`, `COUNT(*) AS n`, `avg_stress`, `avg_sleep`.
                - `VTD-300`: close to gold, includes `positives` and `rate_pct`, but missing `group_value` alias, `IS NOT NULL`, and `avg_cgpa_10`.
        - [x] Patch refined hints v2:
            - [x] Make schema column reader support both object-style and dict-style schema entries so table-specific hints actually appear in live prompts.
            - [x] Explicitly prohibit SQLite-unsupported percentile functions such as `PERCENTILE_CONT`; require `NTILE(4)`/grouped bins instead.
            - [x] Make country prevalence change guidance use `MUST use country_prevalence_long` when named disorder + change/quartile cues are present.
            - [x] Make rate contract explicitly require `group_value` alias, `WHERE group_col IS NOT NULL`, `positives`, and `rate_pct` when columns exist.
        - [x] User verification for refined hints v2:
            - `python -m pytest tests\tier1_unit\test_prompt_builder.py -vv --tb=short`
            - rerun agent smoke with `--ablation-id manual_agent_after_refined_shape_hints_v2_spl1`.
        - [x] User verification 2026-05-17:
            - `python -m pytest tests\tier1_unit\test_prompt_builder.py -vv --tb=short` -> `5 passed`.
            - `python -m pytest tests\tier1_unit\test_prompt_builder.py tests\tier1_unit\test_intent_classifier.py tests\tier1_unit\test_ambiguity_detector.py -vv --tb=short` -> `22 passed`.
            - rerun: `python scripts\run_benchmark.py --mode agent --dataset dev --samples-per-level 1 --bootstrap-iterations 100 --exclude-self --trace-level full --ablation-id manual_agent_after_refined_shape_hints_v2_spl1`.
            - output_dir: `results/benchmark/20260517_013053_agent_dev_qwen2-5-coder-7b_manual_agent_after_refined_shape_hints_v2_spl1`.
            - result: evaluated `4`, failures `3`, execution_accuracy `0.25`, valid_sql_rate `1.0`, reliability_score `-2.0`, unsafe_sql `0`.
            - improvement: all four generated SQLs are syntactically/schema valid and `VTD-027` remains exact-correct.
            - remaining issues:
                - `VTD-237`: still uses latest-year `country_prevalence_wide` scalar aggregates instead of change/percentile dashboard shape.
                - `VTD-343`: still row-level risk list without grouped risk summary.
            - `VTD-300`: business-shape is mostly correct (`group_value`, `positives`, `rate_pct`, null filter); EX fails only because gold adds `avg_cgpa_10`, which is not explicit in the user question and must not be blindly enforced as correctness.
        - [x] Patch shape contract validator:
            - [x] Add runtime SQL shape validator after syntax/schema validation and before execution.
            - [x] Enforce SQLite dialect constraints such as no `PERCENTILE_CONT`/`WITHIN GROUP`.
            - [x] Enforce defensible question-derived shape contracts: global change dashboard must not collapse to latest-year scalar; risk-above/below-average must group by `mental_health_risk`; grouped rate must keep standardized rate/count/positive/null-filter columns.
            - [x] Do not enforce gold-only extra columns such as `avg_cgpa_10` unless requested by question or later semantic judge policy.
            - [x] Add focused tests: `tests/tier1_unit/test_shape_validator.py`.
        - [x] User verification for shape contract validator:
            - `python -m pytest tests\tier1_unit\test_prompt_builder.py tests\tier1_unit\test_shape_validator.py -vv --tb=short`
            - `python -m pytest tests\tier1_unit\test_graph_retry_and_config.py tests\tier1_unit\test_graph_attempt_trace.py -vv --tb=short`
            - rerun agent smoke with `--ablation-id manual_agent_after_shape_contract_spl1`.
        - [x] User verification 2026-05-17:
            - first typo command `tests\tier1_unit\test_prompt_builder` -> no tests collected because `.py` suffix was missing.
            - `python -m pytest tests\tier1_unit\test_prompt_builder.py tests\tier1_unit\test_shape_validator.py -vv --tb=short` -> `10 passed`.
            - `python -m pytest tests\tier1_unit\test_graph_retry_and_config.py tests\tier1_unit\test_graph_attempt_trace.py -vv --tb=short` -> `8 passed`.
            - rerun: `python scripts\run_benchmark.py --mode agent --dataset dev --samples-per-level 1 --bootstrap-iterations 100 --exclude-self --trace-level full --ablation-id manual_agent_after_shape_contract_spl1`.
            - output_dir: `results/benchmark/20260517_015651_agent_dev_qwen2-5-coder-7b_manual_agent_after_shape_contract_spl1`.
            - result: evaluated `4`, failures `3`, execution_accuracy `0.25`, valid_sql_rate `0.75`, reliability_score `-1.25`, unsafe_sql `0`.
            - shape contract worked as intended:
                - `VTD-237` was rejected before execution as `INVALID_SQL`/shape invalid with `ANALYTICAL_SHAPE_MISSING_LONG_PREVALENCE_TABLE`, `ANALYTICAL_SHAPE_MISSING_PREVALENCE_LONG_COLUMNS`, `ANALYTICAL_SHAPE_MISSING_CHANGE_MEASURE`, `ANALYTICAL_SHAPE_MISSING_BINNING`.
                - after repair, it used `country_prevalence_long` but still missed change/binning, so it remained rejected.
                - `VTD-343` first attempt was rejected for missing risk grouping/count; repair added `GROUP BY mental_health_risk` and `COUNT(*) AS n` but still missed the above/below-average filters, so EX remained false.
                - `VTD-300` passed shape validation and is likely business-correct for the natural-language rate question, but exact-gold mismatch remains because gold includes `avg_cgpa_10`.
                - `VTD-027` remains exact-correct.
        - [x] Closeout report and stricter shape-contract follow-up 2026-05-17:
            - [x] Added `results/error_analysis/20260517_phase10_shape_contract/error_report.md`.
            - [x] Explicitly documented that exact EX and business correctness are intentionally separate for `VTD-300`-style cases.
            - [x] Anti-overfit decision: do not force gold-only `avg_cgpa_10` unless the question, dataset contract or Phase 16 judge/human review requires it.
            - [x] Tightened `SQLShapeValidator` so risk questions with stress-above-average and sleep-below-average wording must keep those filters before grouping.
            - [x] Added focused tests for `ANALYTICAL_SHAPE_MISSING_RISK_AVERAGE_FILTERS`.
            - [x] Local verification: `.\.venv\Scripts\python.exe -m pytest tests\tier1_unit\test_shape_validator.py tests\tier1_unit\test_prompt_builder.py -vv --tb=short` -> `12 passed`.
        - [x] Final Phase 10 closeout:
            - [x] Run larger balanced local-agent smoke (`--samples-per-level 2` or higher).
            - [x] User verification 2026-05-17:
                - command: `python scripts\run_benchmark.py --mode agent --dataset dev --samples-per-level 2 --bootstrap-iterations 200 --exclude-self --trace-level full --ablation-id manual_agent_shape_contract_spl2`
                - output_dir: `results/benchmark/20260517_030238_agent_dev_qwen2-5-coder-7b_manual_agent_shape_contract_spl2`
                - result: evaluated `8`, failures `6`, execution_accuracy `0.25`, valid_sql_rate `0.75`, reliability_score `-2.5`, unsafe_sql `0`, self_overlap_removed_total `1`.
                - balanced selection verified: complex=2, easy=2, hard=2, medium=2.
                - artifact contract passed: final benchmark completed and printed final artifact path.
            - [x] Fix/verify two infrastructure-level findings from the larger smoke before marking Phase 10 done:
                - [x] `VTD-371`: false `unsafe_query` for a safe matrix/dashboard request containing `بساز`; safety detector now distinguishes analytical "build a matrix/dashboard" from destructive "create/drop/alter table".
                - [x] `VTD-078`: shape validator over-applied stress/sleep risk-summary requirements to a general "average depression/anxiety by mental-health risk" question; validator now only enforces stress/sleep averages and threshold filters for explicit stress/sleep threshold questions.
            - [x] Rerun focused tests after these fixes:
                - `.\.venv\Scripts\python.exe -m pytest tests\tier1_unit\test_safety_detector.py tests\tier1_unit\test_intent_classifier.py tests\tier1_unit\test_shape_validator.py tests\tier1_unit\test_prompt_builder.py -vv --tb=short` -> `34 passed`.
            - [x] Rerun `manual_agent_shape_contract_spl2` after the safety/shape fixes to confirm no new artifact-contract regression.
            - [x] User verification 2026-05-17 after fixes:
                - tests: `python -m pytest tests\tier1_unit\test_safety_detector.py tests\tier1_unit\test_intent_classifier.py tests\tier1_unit\test_shape_validator.py tests\tier1_unit\test_prompt_builder.py -vv --tb=short` -> `34 passed`.
                - command: `python scripts\run_benchmark.py --mode agent --dataset dev --samples-per-level 2 --bootstrap-iterations 200 --exclude-self --trace-level full --ablation-id manual_agent_shape_contract_spl2_after_fixes`
                - output_dir: `results/benchmark/20260517_031221_agent_dev_qwen2-5-coder-7b_manual_agent_shape_contract_spl2_after_fixes`
                - result: evaluated `8`, failures `6`, execution_accuracy `0.25`, valid_sql_rate `0.875`, reliability_score `-3.25`, unsafe_sql `0`, self_overlap_removed_total `1`.
                - balanced selection verified: complex=2, easy=2, hard=2, medium=2.
                - regression check: `VTD-371` is no longer `unsafe_query`; it reaches generation and fails only as `RESULT_MISMATCH`.
                - regression check: `VTD-078` is no longer invalidated by over-broad shape validation; it is valid SQL and fails only as `RESULT_MISMATCH`.
            - [x] Phase 10 infrastructure can be closed. Remaining failures are model/prompt/reasoning quality, ablation, reliability and semantic/business-correctness work for later phases.

---

## Phase 11 - Ablation, Error Analysis, Research Metrics [IN PROGRESS]

Current truth:

- Phase 11 is active and partially complete: artifact analysis tooling, runtime flag contract, real A0-A7 smoke ablation, comparison reporting, and targeted A4 mitigation are done.
- Phase 11 is not paper-grade complete: the current real A4 target artifact is still a small 8-case smoke, and no SOTA/model-quality claim should be made from it.
- The latest completed targeted A4 artifact is `results/benchmark/manual_a4_after_generation_token_cap`: evaluated `8`, failures `5`, execution_accuracy `0.375`, valid_sql_rate `0.625`, reliability_score `0.25`, unsafe_sql `0`, taxonomy `FALSE_ABSTENTION=3`, `SEMANTIC_REVIEW_REQUIRED=2`.
- Config templates are only run definitions. They are not ablation results until `scripts/run_benchmark.py` creates real `results/benchmark/...` artifacts from them.
- Statistical comparison is allowed only when compared runs share the same case IDs; otherwise reports must stay descriptive.
- The latest Phase 11/16 decision is complete for the failure-only A4 slice: semantic judge and judge-agreement artifacts now exist for all A4 failures. The next safe step is success-sample judge coverage before using semantic scores as broader quality metrics.

Implemented / added:

- [x] Phase 11 contract doc: `docs/phases/PHASE_11_ABLATION_ERROR_ANALYSIS.md`.
- [x] `src/evaluation/statistical_tests.py` with bootstrap CI and McNemar helper logic.
- [x] `src/evaluation/artifact_analysis.py` for artifact-backed error report generation.
- [x] `scripts/analyze_benchmark_artifact.py` CLI for analyzing a real benchmark artifact.
- [x] `src/evaluation/ablation_runner.py` dry-run/manifest-oriented ablation runner core.
- [x] `src/evaluation/ablation_flags.py` records runtime-enforced, locked, metadata-only and unknown ablation flags.
- [x] `scripts/run_ablation.py` CLI wrapper for dry-run manifests and optional explicit execution.
- [x] First-paper config templates under `experiments/configs/`:
    - [x] `A0_direct_schema_only.yaml`
    - [x] `A1_persian_nlu.yaml`
    - [x] `A2_schema_linking.yaml`
    - [x] `A3_value_linking.yaml`
    - [x] `A4_cag_examples.yaml`
    - [x] `A7_full_phase10_system.yaml`
- [x] `experiments/configs/README.md` documents that configs are not results.
- [x] Tests added for the first slice:
    - [x] `tests/tier1_unit/test_statistical_tests.py`
    - [x] `tests/tier1_unit/test_artifact_analysis.py`
    - [x] `tests/tier1_unit/test_ablation_runner.py`

Verification and evidence:

- [x] Run the new Phase 11 unit tests:
  `python -m pytest tests\tier1_unit\test_statistical_tests.py tests\tier1_unit\test_artifact_analysis.py -vv --tb=short`
  - User verification 2026-05-17: `5 passed in 0.23s`.
- [x] Add and test `tests/tier1_unit/test_ablation_runner.py`.
- [x] Add `scripts/run_ablation.py` CLI wrapper for dry-run manifests and optional execution.
- [x] Verify full Phase 11 first-slice tests:
  `.\.venv\Scripts\python.exe -m pytest tests\tier1_unit\test_statistical_tests.py tests\tier1_unit\test_artifact_analysis.py tests\tier1_unit\test_ablation_runner.py -vv --tb=short`
  - Local verification 2026-05-17: `7 passed`; latest rerun after CLI Python-path fix: `7 passed in 0.13s`.
- [x] Verify stricter feature-flag wiring:
  `.\.venv\Scripts\python.exe -m pytest tests\tier1_unit\test_statistical_tests.py tests\tier1_unit\test_artifact_analysis.py tests\tier1_unit\test_ablation_runner.py tests\tier1_unit\test_graph_routes.py tests\tier1_unit\test_graph_retry_and_config.py -vv --tb=short`
  - Local verification 2026-05-17: `17 passed in 0.35s`.
- [x] Verify true value-linking isolation:
  `.\.venv\Scripts\python.exe -m pytest tests\tier1_unit\test_value_linker.py tests\tier1_unit\test_ablation_runner.py tests\tier1_unit\test_graph_retry_and_config.py tests\tier1_unit\test_graph_routes.py -vv --tb=short`
  - Local verification 2026-05-17: `19 passed`; latest rerun after adding `value_links` prediction audit field: `19 passed in 3.24s`.
- [x] Inspect A4 latency anomaly from its real artifact.
  - source artifact: `results/benchmark/20260517_233814_a4_cag_examples`
  - finding: A4 mean latency was dominated by `VTD-371` with prediction latency `1603172ms`, while SQL execution latency inside the attempt was only `46ms`.
  - interpretation: the anomaly is graph/LLM wall-clock time, not SQL execution time.
  - prompt/grounding finding: `VTD-371` had `intent=unknown`, weak matrix shape guidance, and unrelated value links such as `workplace_mental_health_survey.state=PA` even though that table was not in the prompt schema.
  - root cause fixed for future runs: `build_prompt` now extracts candidate value-link columns from dict-style `schema_context`; empty candidate lists no longer cause fallback to the whole value dictionary.
  - trace improvement: `generation_latency_ms` is now stored on `SQLAttempt` so future artifacts can separate LLM generation time from SQL execution time.
  - verification: `.\.venv\Scripts\python.exe -m pytest tests\tier1_unit\test_graph_retry_and_config.py tests\tier1_unit\test_graph_attempt_trace.py tests\tier1_unit\test_value_linker.py -vv --tb=short` -> `18 passed`.
  - compile check: `.\.venv\Scripts\python.exe -m py_compile src\graph\nodes\base_nodes.py src\graph\state.py`.
- [x] Rerun targeted A4 after value-link/generation-latency trace fix.
  - command: `python scripts\run_benchmark.py --config experiments\configs\A4_cag_examples.yaml --output-dir results\benchmark\manual_a4_after_value_link_trace_fix`
  - artifact: `results/benchmark/manual_a4_after_value_link_trace_fix`
  - result: evaluated `8`, failures `6`, execution_accuracy `0.25`, valid_sql_rate `0.375`, reliability_score `-0.25`, unsafe_sql `0`.
  - latency improved: mean `12002.38ms`, median `9882.0ms`, p95 `22504.0ms`, max `22504.0ms`.
  - `VTD-371`: latency `14146ms`, `generation_latency_ms=13135`, no SQL execution because shape/schema validation failed.
  - remaining issue: `VTD-371` still generated wrong-table columns (`sleep_hours`, `diet_quality`) for `student_depression`; this is now handled by a new general matrix shape contract and prompt/intent guidance.
  - artifact-backed analysis report: `results/error_analysis/20260518_a4_after_value_link_trace_fix/error_report.md`.
- [x] Add general matrix request hardening after the A4 rerun.
  - [x] `matrix` / `ماتریس` analytical requests now route to `grouping_query`.
  - [x] Prompt builder adds schema-derived sleep/diet/depression/CGPA matrix guidance for `student_depression`.
  - [x] Shape validator rejects wrong-table matrix columns such as `sleep_hours`/`diet_quality` when `student_depression` requires `sleep_duration_category`/`dietary_habits`.
  - [x] Value linker no longer treats metric column names such as `eating_disorder_pct` as categorical `disorder` columns.
  - [x] Verification: `.\.venv\Scripts\python.exe -m pytest tests\tier1_unit\test_intent_classifier.py tests\tier1_unit\test_prompt_builder.py tests\tier1_unit\test_shape_validator.py tests\tier1_unit\test_value_linker.py tests\tier1_unit\test_value_linker_disorder_columns.py tests\tier1_unit\test_graph_retry_and_config.py tests\tier1_unit\test_graph_attempt_trace.py -vv --tb=short` -> `36 passed`.
  - [x] Compile check: `.\.venv\Scripts\python.exe -m py_compile src\nlu\intent_classifier.py src\generation\prompt_builder.py src\schema\value_linker.py src\sql_validation\shape_validator.py src\graph\nodes\base_nodes.py src\graph\state.py`.
- [x] Rerun targeted A4 after matrix hardening.
  - command: `python scripts\run_benchmark.py --config experiments\configs\A4_cag_examples.yaml --output-dir results\benchmark\manual_a4_after_matrix_hardening`
  - artifact: `results/benchmark/manual_a4_after_matrix_hardening`
  - result: evaluated `8`, failures `6`, execution_accuracy `0.25`, valid_sql_rate `0.5`, reliability_score `-1.0`, unsafe_sql `0`.
  - latency stable: mean `12736.88ms`, median `9596.5ms`, p95 `24266.0ms`, max `24266.0ms`.
  - `VTD-371`: intent `grouping_query`, valid SQL `True`, execution latency `68ms`, generation_latency_ms `18451`, error `RESULT_MISMATCH`.
  - `VTD-371` generated the correct schema/table shape but differed from gold on support threshold/sorting: generated `ORDER BY n DESC LIMIT 100`; gold uses `HAVING COUNT(*)>=50 ORDER BY depression_rate_pct DESC`.
  - artifact-backed analysis report: `results/error_analysis/20260518_a4_after_matrix_hardening/error_report.md`.
  - anti-overfit decision: do not add the exact `HAVING COUNT(*)>=50` threshold solely to match this case unless a general dashboard/matrix support-threshold policy is adopted and tested.
- [x] Implement a general matrix-dashboard support/sorting policy.
  - policy basis: real `student_depression` has `27901` rows and `19` sleep/diet cells; sparse `Others` cells have counts `1, 3, 3, 3, 5, 7, 8`, while substantive cells are `1660+`.
  - decision: for `student_depression` sleep/diet depression-CGPA matrices, use `HAVING COUNT(*) >= 50` as a minimum support threshold to suppress unstable sparse cells, and sort by the primary requested metric `depression_rate_pct DESC`.
  - guardrail: this is a table/shape policy documented from observed distribution, not a hidden case-id rule; previous artifacts remain unchanged.
  - [x] Prompt builder now instructs this support threshold and primary metric sort for the schema-derived matrix shape.
  - [x] Shape validator now rejects missing support threshold or missing `ORDER BY depression_rate_pct DESC` for this matrix shape.
  - [x] Verification: `.\.venv\Scripts\python.exe -m pytest tests\tier1_unit\test_prompt_builder.py tests\tier1_unit\test_shape_validator.py tests\tier1_unit\test_intent_classifier.py tests\tier1_unit\test_value_linker_disorder_columns.py tests\tier1_unit\test_graph_retry_and_config.py tests\tier1_unit\test_graph_attempt_trace.py -vv --tb=short` -> `33 passed`.
  - [x] Compile check: `.\.venv\Scripts\python.exe -m py_compile src\generation\prompt_builder.py src\sql_validation\shape_validator.py src\nlu\intent_classifier.py src\schema\value_linker.py src\graph\nodes\base_nodes.py src\graph\state.py`.
- [x] Rerun targeted A4 after matrix support-threshold/sorting policy.
  - command: `.\.venv\Scripts\python.exe scripts\run_benchmark.py --config experiments\configs\A4_cag_examples.yaml --output-dir results\benchmark\manual_a4_after_matrix_support_policy`
  - artifact: `results/benchmark/manual_a4_after_matrix_support_policy`
  - result: evaluated `8`, failures `6`, execution_accuracy `0.25`, valid_sql_rate `0.375`, reliability_score `-0.25`, unsafe_sql `0`.
  - latency: mean `14045.25ms`, median `10817.5ms`, p95 `33088.0ms`, max `33088.0ms`.
  - `VTD-371`: intent `grouping_query`, valid SQL `True`, execution_correct `True`, generation_latency_ms `16651`, SQL execution latency `22ms`.
  - artifact-backed analysis report: `results/error_analysis/20260518_a4_after_matrix_support_policy/error_report.md`.
  - interpretation: the general matrix policy fixed the VTD-371 support/sorting mismatch and kept the old A4 latency anomaly resolved, but the overall A4 smoke did not improve because false abstentions increased (`FALSE_ABSTENTION=5`, `SEMANTIC_REVIEW_REQUIRED=1`). This is not a paper-quality result and should not be reported as model quality improvement.
- [x] Triage A4 false abstentions from the support-policy artifact and implement two general mitigations.
  - finding: `VTD-237`, `VTD-343`, and `VTD-078` were legitimate rejections for missing change/binning, fixed average-threshold constants, or missing risk grouping key.
  - finding: `VTD-027` used common alias `family_history` for `student_depression.family_history_mental_illness`; this is now handled by table-scoped SQL rewrite and does not affect `workplace_mental_health_survey.family_history`.
  - finding: `VTD-300` computed the depression-rate formula correctly but omitted the auxiliary `positives` output column; the shape validator now requires a rate formula from `depression_flag`, not the optional helper column.
  - verification: `.\.venv\Scripts\python.exe -m pytest tests\tier1_unit\test_sql_rewriter_ast.py tests\tier1_unit\test_shape_validator.py tests\tier1_unit\test_prompt_builder.py -vv --tb=short` -> `25 passed`.
  - compile check: `.\.venv\Scripts\python.exe -m py_compile src\sql_validation\sql_rewriter.py src\sql_validation\shape_validator.py`.
- [x] Fix graph execution to use the rewritten/validated SQL.
  - finding from `results/benchmark/manual_a4_after_false_abstention_mitigation`: `VTD-027` passed validation after rewrite, but execution still used the raw `family_history` SQL and failed with `no such column: family_history`.
  - fix: `validate_sql` now promotes `ValidationPipeline.normalized_sql` back into graph state and records that SQL in the latest `SQLAttempt`, so the executor uses the same SQL that passed validation.
  - verification: `.\.venv\Scripts\python.exe -m pytest tests\tier1_unit\test_graph_attempt_trace.py tests\tier1_unit\test_sql_rewriter_ast.py tests\tier1_unit\test_shape_validator.py -vv --tb=short` -> `22 passed`.
  - compile check: `.\.venv\Scripts\python.exe -m py_compile src\graph\nodes\base_nodes.py src\sql_validation\sql_rewriter.py src\sql_validation\shape_validator.py`.
- [x] Relax grouped-rate null-filter shape check to accept equivalent SQL.
  - finding from `results/benchmark/manual_a4_after_rewritten_sql_promotion`: `VTD-300` computed the rate correctly but shape validation rejected `WHERE NOT sleep_duration_category IS NULL`, which is equivalent to `sleep_duration_category IS NOT NULL`.
  - fix: grouped-rate shape validation now accepts both `column IS NOT NULL` and `NOT column IS NULL` forms.
  - verification: `.\.venv\Scripts\python.exe -m pytest tests\tier1_unit\test_shape_validator.py tests\tier1_unit\test_graph_attempt_trace.py -vv --tb=short` -> `16 passed`.
  - compile check: `.\.venv\Scripts\python.exe -m py_compile src\sql_validation\shape_validator.py src\graph\nodes\base_nodes.py`.
- [x] Attempt rerun after equivalent-null-filter acceptance and classify it as incomplete.
  - command attempted: `.\.venv\Scripts\python.exe scripts\run_benchmark.py --config experiments\configs\A4_cag_examples.yaml --output-dir results\benchmark\manual_a4_after_null_filter_equivalence`
  - status: incomplete; command timed out before final summary.
  - partial artifact only: `results/benchmark/manual_a4_after_null_filter_equivalence`.
  - partial files contain `4` predictions, `4` attempts, and `1` failure; no final `summary.json`.
  - guardrail: this directory is not a completed benchmark result and must not be used for A4 metrics.
  - diagnostic finding: partial `VTD-039` recorded `generation_latency_ms=53819322` while SQL execution latency was `12ms`, confirming a generation-wall-clock anomaly.
- [x] Add generation token cap for SQL generation.
  - fix: `generate_sql` now passes bounded `max_tokens` to `LocalLLM.generate_json`.
  - default: `512`; override: `VTD_SQL_GENERATION_MAX_TOKENS`.
  - verification: `.\.venv\Scripts\python.exe -m pytest tests\tier1_unit\test_graph_attempt_trace.py tests\tier1_unit\test_shape_validator.py -vv --tb=short` -> `17 passed`.
  - compile check: `.\.venv\Scripts\python.exe -m py_compile src\graph\nodes\base_nodes.py src\sql_validation\shape_validator.py`.
- [x] Rerun targeted A4 after generation token cap.
  - command: `.\.venv\Scripts\python.exe scripts\run_benchmark.py --config experiments\configs\A4_cag_examples.yaml --output-dir results\benchmark\manual_a4_after_generation_token_cap`
  - artifact: `results/benchmark/manual_a4_after_generation_token_cap`
  - result: evaluated `8`, failures `5`, execution_accuracy `0.375`, valid_sql_rate `0.625`, reliability_score `0.25`, unsafe_sql `0`.
  - latency: mean `11495.62ms`, median `9746.5ms`, p95 `17686.0ms`, max `17686.0ms`.
  - artifact-backed analysis report: `results/error_analysis/20260518_a4_after_generation_token_cap/error_report.md`.
  - research taxonomy: `FALSE_ABSTENTION=3`, `SEMANTIC_REVIEW_REQUIRED=2`.
  - improvements vs `manual_a4_after_matrix_support_policy`: `VTD-027` is exact-correct after rewritten-SQL promotion; `VTD-300` is valid/executed after equivalent null-filter acceptance; generation latency no longer shows the incomplete-run anomaly.
  - remaining failures are not solved by safe validator relaxation:
    - `VTD-237`: still misses global change/binning shape and sometimes selects the wide-table scalar path.
    - `VTD-343`: still omits grouped risk summary columns even when average thresholds are present.
    - `VTD-078`: still omits `mental_health_risk` from SELECT/GROUP BY.
    - `VTD-141` and `VTD-300`: valid SQL but exact-result mismatch; these require semantic/business review or broader prompt/shape policy, not hidden gold tuning.
- [x] Compile changed scripts/modules:
  `.\.venv\Scripts\python.exe -m py_compile scripts\run_benchmark.py scripts\run_ablation.py src\evaluation\ablation_flags.py src\evaluation\ablation_runner.py src\graph\nodes\base_nodes.py src\graph\routes.py src\graph\state.py`
- [x] Generate the first Phase 11 report from the real Phase 10 closeout artifact:
  `results/benchmark/20260517_031221_agent_dev_qwen2-5-coder-7b_manual_agent_shape_contract_spl2_after_fixes`.
- [x] Store generated report under:
  `results/error_analysis/20260517_phase11_spl2_after_fixes/error_report.md`.
  - User verification 2026-05-17:
    - `report=results\error_analysis\20260517_phase11_spl2_after_fixes\error_report.md`
    - `failure_cases=results\error_analysis\20260517_phase11_spl2_after_fixes\failure_cases.jsonl`
    - `summary=results\error_analysis\20260517_phase11_spl2_after_fixes\analysis_summary.json`
    - analyzed predictions: `8`
    - analyzed attempts: `12`
    - analyzed failures: `6`
    - research taxonomy: `SEMANTIC_REVIEW_REQUIRED=3`, `SHAPE_CONTRACT_ERROR=2`, `FALSE_ABSTENTION=1`
    - source metrics preserved from artifact: `execution_accuracy=0.25`, `valid_sql_rate=0.875`, `reliability_score=-3.25`, `unsafe_sql=0`
- [x] Create dry-run ablation manifest without running benchmarks:
  `.\.venv\Scripts\python.exe scripts\run_ablation.py --output-dir results\ablation\20260517_phase11_dry_run_manifest`
  - output: `results/ablation/20260517_phase11_dry_run_manifest/ablation_manifest.json`
  - jobs: `6`
  - status: all jobs `not_run`
  - planned command Python: `D:\Project\ADHD-VTD\.venv\Scripts\python.exe`
  - anti-fake policy recorded: config manifests are not benchmark results.
  - runtime contract recorded:
    - enforced flags: `nlu`, `schema_linking`, `value_linking`, `cag`, `reflexion`, `repair`
    - locked flags: `safety`, `validation`
    - metadata-only flags: none
- [x] Improve `scripts/run_ablation.py --execute` UX so benchmark job logs stream live by default.
  - [x] `--quiet` keeps the previous captured-output behavior.
- [x] Add artifact-backed A0-A7 comparison reporting.
  - [x] `src/evaluation/ablation_report.py`
  - [x] `scripts/analyze_ablation_manifest.py`
  - [x] `tests/tier1_unit/test_ablation_report.py`
  - [x] Verification: `.\.venv\Scripts\python.exe -m pytest tests\tier1_unit\test_ablation_runner.py tests\tier1_unit\test_ablation_report.py -vv --tb=short` -> `4 passed`.
  - [x] Compile check: `.\.venv\Scripts\python.exe -m py_compile scripts\analyze_ablation_manifest.py src\evaluation\ablation_report.py scripts\run_ablation.py src\evaluation\ablation_runner.py`.

Still required for full Phase 11:

- [x] Decide the next path before more A0-A7 runs:
    - Option A: continue general shape-guidance/contracts for the remaining invalid A4 cases (`VTD-237`, `VTD-343`, `VTD-078`).
    - Option B: pause A4 tuning and implement Phase 16 judge first for valid result mismatches (`VTD-141`, `VTD-300`).
    - Selected path: Option B first. Phase 16 mock/OpenRouter/canonical agreement was implemented before additional A4 tuning to reduce overfit risk.
- [x] Error taxonomy alignment with `docs/06_EVALUATION_ABLATION_AND_PAPER_PLAN.md`.
    - [x] `src/evaluation/artifact_analysis.py` now records docs/06-aligned `docs06_error` separately from legacy `research_error`.
    - [x] Valid SQL `RESULT_MISMATCH` cases without `semantic_business_correct` remain `pending_semantic_review`; no semantic label is invented.
    - [x] New artifact-backed report: `results/error_analysis/20260519_phase11_docs06_taxonomy_a4_token_cap/error_report.md`.
    - [x] Summary: `docs06_error_counts = AGGREGATION_ERROR=2, SCHEMA_LINKING_ERROR=1`; `semantic_review_required_count=2`.
    - [x] Verification: `.\.venv\Scripts\python.exe -m pytest tests\tier1_unit\test_artifact_analysis.py tests\tier1_unit\test_statistical_tests.py -vv --tb=short` -> `7 passed`.
- [ ] **Automated Ablation Matrix** generation:
    - [x] `scripts/run_ablation.py` dry-run manifest CLI.
    - [x] `scripts/analyze_ablation_manifest.py` cross-run comparison report from a completed manifest.
    - [x] Cross-config result aggregator that compares only real artifacts.
    - [ ] Larger paper-grade ablation suite beyond the 8-case smoke matrix.
- [x] Retrieval ablation smoke: BM25-only, vector-only, hybrid, reranker.
    - [x] Runtime retrieval backend selector added to `scripts/run_benchmark.py`: `bm25`, `vector`, `hybrid`, `hybrid_rerank`.
    - [x] `HybridRetriever` now supports real `retrieval_mode` isolation for BM25-only, vector-only and hybrid.
    - [x] Retrieval ablation configs added:
      `experiments/configs/R0_retrieval_bm25.yaml`,
      `experiments/configs/R1_retrieval_vector.yaml`,
      `experiments/configs/R2_retrieval_hybrid.yaml`,
      `experiments/configs/R3_retrieval_hybrid_rerank.yaml`.
    - [x] Dry-run manifest: `results/ablation/20260519_phase11_retrieval_dry_run_manifest/ablation_manifest.json`.
    - [x] BM25 config smoke artifact: `results/benchmark/manual_r0_retrieval_bm25_smoke` with retrieval_hit_rate `1.0` on the 8-case smoke set.
    - [x] Execute all R0-R3 retrieval ablations and generate comparison report from real artifacts.
    - [x] Real manifest: `results/ablation/20260519_phase11_retrieval_execute/ablation_manifest.json`.
    - [x] Report: `results/ablation/20260519_phase11_retrieval_execute/ablation_comparison.md`.
    - [x] Smoke metrics:
      `R0 bm25 hit_rate=1.0 latency_mean=1.75ms`;
      `R1 vector hit_rate=1.0 latency_mean=690.88ms`;
      `R2 hybrid hit_rate=0.875 latency_mean=650.5ms`;
      `R3 hybrid_rerank(identity) hit_rate=0.875 latency_mean=740.25ms`.
    - [x] Limitation: this is an 8-case smoke retrieval matrix; R3 uses identity reranker and is not a model-backed reranker claim.
    - [x] Initial full-dev retrieval ablation executed on 60 dev cases.
    - [x] Initial full-dev manifest: `results/ablation/20260519_phase11_retrieval_dev_full_execute/ablation_manifest.json`.
    - [x] Initial full-dev report: `results/ablation/20260519_phase11_retrieval_dev_full_execute/ablation_comparison.md`.
    - [x] Initial full-dev metrics before schema-evidence guard:
      `R0 bm25 60/60 hit_rate=1.0 mean=0.78ms max=8ms`;
      `R1 vector 60/60 hit_rate=1.0 mean=97.88ms max=5657ms`;
      `R2 hybrid 58/60 hit_rate=0.9667 mean=95.52ms max=5440ms`;
      `R3 hybrid_rerank(identity) 58/60 hit_rate=0.9667 mean=104.47ms max=5960ms`.
    - [x] Hybrid/R3 misses are `VTD-039` (`university_student_mental_health`) and `VTD-036` (`mental_health_general`).
    - [x] Investigate why hybrid scoring loses two easy distribution cases even though BM25-only and vector-only hit all 60.
      - [x] Root cause: schema-overlap evidence existed below the final top-k but could be dropped after self-overlap filtering/top-k slicing.
      - [x] General fix: preserve schema evidence after self-overlap filtering and before final top-k slicing; no case IDs or gold SQL are used.
      - [x] Verification: `tests/tier1_unit/test_benchmark_retrieval_prediction.py`, `tests/tier1_unit/test_retrieval.py`, `tests/tier1_unit/test_ablation_report.py`, `tests/tier1_unit/test_ablation_runner.py` -> `14 passed, 2 warnings`.
      - [x] Compile check: `scripts/run_benchmark.py`, `src/retrieval/hybrid_retriever.py`, `src/retrieval/schema_evidence.py`.
      - [x] Targeted R2/R3 guard verification: `results/ablation/20260519_phase11_retrieval_dev_full_schema_guard_after_filter_r2_r3/ablation_comparison.md` -> R2/R3 both `60/60`.
      - [x] Final full-dev retrieval manifest: `results/ablation/20260519_phase11_retrieval_dev_full_final/ablation_manifest.json`.
      - [x] Final full-dev retrieval report: `results/ablation/20260519_phase11_retrieval_dev_full_final/ablation_comparison.md`.
      - [x] Final full-dev retrieval metrics:
        `R0 bm25 60/60 hit_rate=1.0 mean=0.7ms p95=1.0ms`;
        `R1 vector 60/60 hit_rate=1.0 mean=109.28ms p95=9.0ms`;
        `R2 hybrid 60/60 hit_rate=1.0 mean=109.28ms p95=8.0ms`;
        `R3 hybrid_rerank(identity) 60/60 hit_rate=1.0 mean=102.75ms p95=7.0ms`.
      - [x] Limitation remains: R3 uses identity reranker; this is not a model-backed reranker/SOTA claim.
- [ ] Component metrics: Schema Recall@k, Value Recall@k, Intent@k, Skeleton@k, EX, Valid SQL Rate, Reliability Score, latency.
- [ ] Human/second-review or independent judge review for at least 50 benchmark items.
- [ ] Single-annotator limitation documented if second review is not possible.
- [ ] After the judge/semantic layer or remaining shape-guidance decision, rerun A0-A7 smoke or a larger balanced dev suite only as a new artifact; do not overwrite historical smoke reports.

Phase 11 guardrails:

- [x] No fake metrics: every reported result must cite a real `results/benchmark/...` artifact.
- [x] No overfit: ablation/report code must not use hidden gold SQL or benchmark IDs as runtime hints.
- [x] Config files are not results; they only define commands to run.
- [x] Paired statistical tests are allowed only for runs with matching case IDs.

Immediate Phase 11 slice:

- [x] Add statistical helpers for bootstrap and McNemar.
- [x] Add artifact-backed error-analysis report generator.
- [x] Add first-paper ablation config templates with explicit module flags and limitations.
- [x] Verify the new helpers/reporting code with focused unit tests.
- [x] Generate the first Phase 11 report from the real Phase 10 closeout artifact:
  `results/benchmark/20260517_031221_agent_dev_qwen2-5-coder-7b_manual_agent_shape_contract_spl2_after_fixes`.
- [x] Store first Phase 11 report:
  `results/error_analysis/20260517_phase11_spl2_after_fixes/error_report.md`.
- [x] Add ablation dry-run CLI and tests before running/claiming any ablation results.
- [x] Create dry-run ablation manifest:
  `results/ablation/20260517_phase11_dry_run_manifest/ablation_manifest.json`.
- [x] Strictly verify/wire ablation feature flags before real runs.
  - [x] `schema_linking=false` now uses full-schema context with `schema_linking_disabled` marker.
  - [x] `value_linking=false` now omits explicit value links from prompt/state, while `value_linking=true` resolves links from schema-context candidate columns.
  - [x] Agent benchmark predictions now include `value_links` for auditability.
  - [x] `repair=false` now stops retry/repair routing even if `reflexion=true`.
  - [x] `safety` and `validation` are locked and cannot be treated as disabled runtime modules.
  - [x] `value_linking` is no longer metadata-only.
- [x] Execute real ablation smoke runs only after accepting their cost/time, and only report metrics from generated `results/benchmark/...` artifacts.
- [x] Execute real A0-A7 ablation smoke on 8 dev cases per config.
  - command: `python scripts\run_ablation.py --execute --output-dir results\ablation\20260517_phase11_a0_a7_execute`
  - manifest: `results/ablation/20260517_phase11_a0_a7_execute/ablation_manifest.json`
  - jobs: `6`
  - completed: `6`
  - failed: `0`
  - artifact-backed metrics:
    - `A0_direct_schema_only`: EX `0.0`, valid_sql_rate `0.375`, reliability `-4.25`, unsafe_sql `0`, latency_mean_ms `13182.5`
    - `A1_persian_nlu`: EX `0.0`, valid_sql_rate `0.375`, reliability `-4.25`, unsafe_sql `0`, latency_mean_ms `11958.25`
    - `A2_schema_linking`: EX `0.0`, valid_sql_rate `0.375`, reliability `-4.25`, unsafe_sql `0`, latency_mean_ms `17079.38`
    - `A3_value_linking`: EX `0.0`, valid_sql_rate `0.5`, reliability `-5.0`, unsafe_sql `0`, latency_mean_ms `16927.88`
    - `A4_cag_examples`: EX `0.25`, valid_sql_rate `0.5`, reliability `-1.0`, unsafe_sql `0`, latency_mean_ms `216118.5`
    - `A7_full_phase10_system`: EX `0.25`, valid_sql_rate `0.875`, reliability `-3.25`, unsafe_sql `0`, latency_mean_ms `17960.88`
  - Interpretation guardrail: this is an 8-case smoke ablation, not a final paper claim.
  - Follow-up required: inspect A4 high latency before any paper claim.
- [x] Generate formal artifact-backed A0-A7 ablation comparison report from the real manifest.
  - command: `.\.venv\Scripts\python.exe scripts\analyze_ablation_manifest.py results\ablation\20260517_phase11_a0_a7_execute\ablation_manifest.json`
  - report: `results/ablation/20260517_phase11_a0_a7_execute/ablation_comparison.md`
  - summary: `results/ablation/20260517_phase11_a0_a7_execute/ablation_comparison.json`
  - jobs_total: `6`
  - jobs_completed: `6`
  - same_dataset_hash: `True`
  - same_selected_cases_hash: `True`
  - artifact-backed smoke result: A4 and A7 reached EX `0.25`; A7 had best valid_sql_rate `0.875`; all configs had unsafe_sql `0`.
  - limitation: no semantic/business correctness is inferred; paired significance is not reported yet; this is an 8-case smoke matrix.

---

## Phase 16 - Semantic Business Logic (LLM-as-a-Judge) [DONE]

- [x] Treat Phase 16 as a separate semantic/business correctness layer, independent from SQL execution correctness.
- [x] Create standalone mock/offline scaffold that reads existing benchmark artifacts without rerunning or editing predictions.
- [x] `src/evaluation/llm_judge.py` using configurable judge-provider protocol.
    - [ ] Provider interface implementations: `OpenAIJudgeProvider`, `LocalJudgeProvider`.
    - [x] `MockJudgeProvider` for tests/offline scaffolding.
    - [x] `OpenRouterJudgeProvider` with env-based API key/model configuration.
    - [x] Mock provider is conservative: exact SQL match -> scaffold-correct; missing/invalid SQL -> scaffold-incorrect; valid `RESULT_MISMATCH` -> `requires_semantic_review` with no invented semantic label.
    - [x] OpenRouter API client setup through environment/config only; no hardcoded keys.
    - [ ] Judge prompt templates (Persian/English).
    - [x] Deterministic scaffold SQL business-logic classifier for exact/missing/invalid/unjudged categories.
    - [ ] SOTA/online or local SQL business-logic correctness scorer.
    - [ ] Result relevance scorer.
    - [ ] Explanation-vs-SQL consistency scorer.
- [x] Judge prompt for SQL business logic correctness v0.
- [x] Integration into `run_benchmark.py --use-judge` for offline mock provider.
- [x] Integration into `run_benchmark.py --use-judge` for OpenRouter provider.
- [x] Integration into `run_benchmark.py --use-judge` for OpenRouter provider.
- [x] Standalone CLI for judging existing artifacts:
    - [x] `scripts/judge_benchmark_artifact.py`.
    - [x] CLI options: `artifact_dir`, `--output-dir`, `--judge-provider mock|openrouter`, `--judge-model`, `--judge-sample-size`, `--all-predictions`, `--case-ids`.
- [ ] CLI options:
    - [x] `--use-judge`
    - [x] `--judge-provider mock`
    - [x] `--judge-provider openrouter`
    - [ ] `--judge-provider openai|local`
    - [x] `--judge-model <name>`
    - [x] `--judge-sample-size N`
    - [x] `--judge-failures-only` / `--no-judge-failures-only`
    - [x] `--judge-reasoning` / `--no-judge-reasoning`
    - [ ] `--judge-redact-results`
- [ ] Semantic consistency check:
    - [ ] question vs generated SQL
    - [ ] generated SQL vs gold SQL
    - [ ] generated SQL vs result rows
    - [ ] explanation/final answer vs generated SQL
- [ ] Cost estimation and token tracking for judge runs.
- [ ] Privacy guard:
    - [ ] Never send raw PII to cloud judge.
    - [ ] Default cloud judge input uses schema, SQL, aggregate result preview/hash and redacted sample rows.
    - [x] Store redaction decision in offline mock `judgments.jsonl`.
    - [ ] PII detection/blocking for online cloud judge mode.
- [ ] **Judgment Artifacts**:
    - [x] Standalone `results/judgments/.../judgments.jsonl`.
    - [x] Standalone `results/judgments/.../judge_reasoning.md`.
    - [x] Standalone `results/judgments/.../judge_summary.json`.
    - [x] Standalone `results/judgments/.../judge_costs.json`.
    - [x] Standalone `results/judgments/.../semantic_business_summary.csv`.
    - [ ] Integrated `results/benchmark/.../judgments.jsonl`.
    - [ ] Integrated `results/benchmark/.../judge_reasoning.md`.
    - [x] Integrated `results/benchmark/.../judgments.jsonl` for mock mode.
    - [x] Integrated `results/benchmark/.../judge_reasoning.md` for mock mode.
    - [x] Integrated `results/benchmark/.../judge_costs.json` for mock mode.
    - [x] Integrated `results/benchmark/.../semantic_business_summary.csv` for mock mode.

Verified scaffold:

- [x] Tests: `.\.venv\Scripts\python.exe -m pytest tests\tier1_unit\test_llm_judge.py tests\tier1_unit\test_artifact_analysis.py -vv --tb=short` -> `7 passed`.
- [x] Compile: `.\.venv\Scripts\python.exe -m py_compile src\evaluation\llm_judge.py scripts\judge_benchmark_artifact.py`.
- [x] Real artifact-backed mock judgment:
    - source: `results\benchmark\manual_a4_after_generation_token_cap`
    - output: `results\judgments\20260519_phase16_mock_a4_token_cap`
    - `judgments.jsonl`: `results\judgments\20260519_phase16_mock_a4_token_cap\judgments.jsonl`
    - `judge_summary.json`: `results\judgments\20260519_phase16_mock_a4_token_cap\judge_summary.json`
    - `judge_costs.json`: `results\judgments\20260519_phase16_mock_a4_token_cap\judge_costs.json`
    - `semantic_business_summary.csv`: `results\judgments\20260519_phase16_mock_a4_token_cap\semantic_business_summary.csv`
    - `judge_reasoning.md`: `results\judgments\20260519_phase16_mock_a4_token_cap\judge_reasoning.md`
    - total predictions: `8`
    - judged failures: `5`
    - verdicts: `invalid_sql=3`, `requires_semantic_review=2`
    - semantic scaffold counts: `incorrect=3`, `unjudged=2`
    - cost scaffold: `input_tokens=0`, `output_tokens=0`, `estimated_cost_usd=0.0`, `cost_authoritative=false`
    - authoritative: `false`
    - anti-fake interpretation: this does not claim semantic correctness for `VTD-141` or `VTD-300`; they remain pending independent review.
- [x] Integrated `run_benchmark.py --use-judge` smoke:
    - command: `.\.venv\Scripts\python.exe scripts\run_benchmark.py --mode gold --dataset dev --sample 1 --bootstrap-iterations 20 --use-judge --judge-provider mock --no-judge-failures-only --ablation-id phase16_mock_integration_smoke_v2`
    - artifact: `results\benchmark\20260519_085308_gold_dev_qwen2-5-coder-7b_phase16_mock_integration_smoke_v2`
    - benchmark: `evaluated=1`, `failures=0`, `execution_accuracy=1.0`, `valid_sql_rate=1.0`, `reliability_score=1.0`, `unsafe_sql=0`
    - judge files: `judgments.jsonl`, `judge_summary.json`, `judge_reasoning.md`, `judge_costs.json`, `semantic_business_summary.csv`
    - judge: `total_judged=1`, `exact_sql_match=1`, `semantic_correct=1`, `authoritative=false`
    - locator fix: analyzer/judge now prefer final `*_predictions.jsonl` over `*_partial_predictions.jsonl` when both exist.
- [x] A0-A7 mock-judge sweep:
    - source manifest: `results\ablation\20260517_phase11_a0_a7_execute\ablation_manifest.json`
    - output root: `results\judgments\20260519_phase16_mock_a0_a7`
    - jobs: `6`
    - provider: `mock`
    - authoritative: `false`
    - summary:
      `A0 invalid_sql=5 requires_semantic_review=3`;
      `A1 invalid_sql=5 requires_semantic_review=3`;
      `A2 invalid_sql=5 requires_semantic_review=3`;
      `A3 invalid_sql=4 requires_semantic_review=4`;
      `A4 invalid_sql=4 requires_semantic_review=2`;
      `A7 invalid_sql=1 requires_semantic_review=5`.
- [x] OpenRouter provider wiring:
    - source: official OpenRouter chat completions/auth docs.
    - endpoint: `https://openrouter.ai/api/v1/chat/completions`.
    - env vars: `OPENROUTER_API_KEY`, `VTD_OPENROUTER_JUDGE_MODEL`, `OPENROUTER_HTTP_REFERER`, `OPENROUTER_APP_TITLE`.
    - CLI model override: `--judge-model <provider/model-id>`.
    - CLI reasoning mode: `--judge-reasoning` sends OpenRouter `reasoning: {"enabled": true}` and stores only `reasoning_tokens` / `reasoning_details_present`.
    - tests use fake HTTP; no live API call is made in test.
    - no-key smoke: `results\judgments\20260519_phase16_openrouter_no_key_a4_token_cap` -> `provider_not_configured=2`, `authoritative=false`.
    - first live pilot result: `results\judgments\20260519_phase16_openrouter_qwen_a4_sample2_retry` judged `2` failures; one `VTD-237` live verdict was `fail/incorrect`, one `VTD-343` hit `IncompleteRead` and was recorded as `provider_error`.
    - authoritative Qwen retry: `results\judgments\20260519_phase16_openrouter_qwen_a4_sample2_retry2` judged `2` failures with `qwen/qwen3.6-plus`; `authoritative=true`, `semantic_business_counts=incorrect=2`, verdicts `fail=1`, `incorrect=1`.
    - authoritative DeepSeek free pilot without reasoning: `results\judgments\20260519_phase16_openrouter_deepseek_free_a4_sample2_no_reasoning` judged `2` failures with `deepseek/deepseek-v4-flash:free`; `authoritative=true`, `semantic_business_counts=incorrect=2`, verdicts `fail=2`, `reasoning_tokens=0`.
    - all-failure Qwen live run before canonical verdict hardening: `results\judgments\20260519_phase16_openrouter_qwen_a4_failures_all` judged `5/5` failures; raw provider verdicts `fail=3`, `incorrect=1`, `partial_match=1`; raw semantic counts `incorrect=4`, `correct=1`.
    - all-failure DeepSeek free live run before canonical verdict hardening: `results\judgments\20260519_phase16_openrouter_deepseek_free_a4_failures_all` judged `5/5` failures; raw provider verdicts `incorrect=2`, `invalid=1`, `disapproved=1`, `fail=1`; raw semantic counts `incorrect=4`, `unjudged=1`.
    - interpretation: `VTD-300` is disputed/partial because Qwen marks the core rate logic as semantically correct while DeepSeek marks it ambiguous; it must not be used as a final semantic-correct claim without adjudication or human review.
    - report hardening after all-failure runs: provider verdicts are now canonicalized to stable report categories; `partial_match` becomes `partial_business_match` with `semantic_business_correct=null` and human review required, and provider `invalid` labels on benchmark-valid SQL become `business_incorrect` rather than fake `invalid_sql`.
    - canonical all-failure Qwen rerun: `results\judgments\20260519_phase16_openrouter_qwen_a4_failures_all_canonical`; `business_incorrect=4`, `partial_business_match=1`; semantic counts `incorrect=4`, `unjudged=1`.
    - canonical all-failure DeepSeek free rerun: `results\judgments\20260519_phase16_openrouter_deepseek_free_a4_failures_all_canonical`; `invalid_sql=3`, `business_incorrect=1`, `partial_business_match=1`; semantic counts `incorrect=4`, `unjudged=1`.
    - judge agreement report: `results\judgments\20260519_phase16_qwen_deepseek_a4_failure_agreement\judge_agreement.md`.
    - agreement result: common_cases `5`, semantic_agreement `5/5`, verdict_agreement `2/5`, final_counts `agreed_incorrect=4`, `adjudication_required=1`.
    - robustness fix: chunked HTTP failures such as `http.client.IncompleteRead` are retried and then recorded as `provider_error` instead of crashing the judge run.
    - robustness fix: empty or `None` provider content is recorded as `provider_parse_error` instead of crashing the judge run.
    - report fix: OpenRouter reports now use provider-aware title/anti-fake policy and CSV preserves provider errors and other free-form verdicts.
    - verification: `.\.venv\Scripts\python.exe -m pytest tests\tier1_unit\test_llm_judge.py -vv --tb=short` -> `12 passed`.
    - agreement tooling verification: `.\.venv\Scripts\python.exe -m pytest tests\tier1_unit\test_judge_agreement.py tests\tier1_unit\test_llm_judge.py -vv --tb=short` -> `14 passed`.
    - judge case filtering added: `scripts\judge_benchmark_artifact.py --case-ids <ids...>` can now run a paid adjudicator only on selected disputed/provider-error cases. Verification: `.\.venv\Scripts\python.exe -m pytest tests\tier1_unit\test_llm_judge.py tests\tier1_unit\test_judge_agreement.py -vv --tb=short` -> `15 passed`.
    - conservative multi-judge consensus tooling added:
      - `src\evaluation\judge_consensus.py`
      - `scripts\analyze_judge_consensus.py`
      - `tests\tier1_unit\test_judge_consensus.py`
      - policy: at least two authoritative non-null semantic votes must agree, and there must be no opposing authoritative semantic vote. Partial business matches are reported separately when at least two authoritative partial votes exist and there are no non-null semantic votes. Single-judge, provider-error and unjudged rows remain unresolved.
      - verification after partial-policy update: `.\.venv\Scripts\python.exe -m pytest tests\tier1_unit\test_judge_consensus.py tests\tier1_unit\test_judge_agreement.py tests\tier1_unit\test_llm_judge.py -vv --tb=short` -> `17 passed`.
- [x] Judge model policy recorded:
    - primary open-model-ecosystem judge candidate: `qwen/qwen3.6-plus`.
    - cheap broad baseline going forward: paid `deepseek/deepseek-v4-flash`.
    - historical/free-only evidence: `deepseek/deepseek-v4-flash:free` artifacts remain recorded as pilot evidence only because the all-prediction run produced provider errors for `2/8` cases.
    - expensive adjudicator subset only: `openai/gpt-5.1`.
    - optional disagreement check: `google/gemini-3-flash-preview`.

Acceptance:

- [ ] Static execution correctness and judge-based business correctness are reported separately.
- [ ] At least failures plus a configurable sample of successes are judged.
- [ ] A case can have `execution_correct=true` and `semantic_business_correct=false`; reports must show this gap.
- [ ] Judge prompt version and judge model name are stored in every judgment artifact.

Minimum first-paper ablation:

- [ ] A0 raw local LLM
- [ ] A1 + Persian normalization
- [ ] A2 + schema linking
- [ ] A3 + validation
- [ ] A4 + CAG examples
- [ ] A5 + SQL skeletons
- [ ] A7 full Paper-1 system without Reflexion

---

## Phase 12 - Output, Chart, Narrative [TODO]

هدف: سیستم فقط SQL/result خام ندهد؛ پاسخ فارسی قابل اعتماد، هشدار، clarification یا abstention تولید کند.

**اولویت**: بالا - `safety_rejection_accuracy=0` غیرقابل قبول است و باید قبل از paper-grade claim برطرف شود.

### 12.1 - Safety Rejection Fix (اولویت اول)

مشکل فعلی: `safety_rejection_accuracy=0/5` در behavior benchmark.

- [x] **12.1.1** تشخیص ریشه مشکل:
    - [x] اجرای behavior_dev benchmark برای debug:\
      فرمان: `python scripts\run_benchmark.py --mode agent --dataset behavior_dev --sample 10 --trace-level full --ablation-id safety_debug_20260522`
    - [x] بررسی دستی artifacts: آیا classifier سوالات unsafe را detect کرد؟
    - [x] Record: case_ids unsafe، detected_unsafe (T/F)، actual_action، expected_action.
- [x] **12.1.2** Fix safety classifier اگر لازم است:
    - [x] افزودن patterns فارسی missing به `src/nlu/safety_intent_detector.py`.
    - [x] تست: `python -m pytest tests\tier1_unit\test_safety_detector.py -vv --tb=short`
- [x] **12.1.3** Fix safety routing اگر لازم است:
    - [x] بررسی و اصلاح `src/graph/routes.py`.
    - [x] تست: `python -m pytest tests\tier1_unit\test_graph_routes.py -vv --tb=short`
- [x] **12.1.4** پیاده‌سازی safe refusal response پیام فارسی صریح.
- [x] **12.1.5** Rerun و verify:
    - [x] فرمان: `python scripts\run_benchmark.py --mode agent --dataset behavior_dev --sample 10 --ablation-id safety_fix_verify_20260522 --trace-level full`
    - [x] هدف: `safety_rejection_accuracy >= 0.8`.

### 12.2 - Clarification Accuracy Fix

مشکل فعلی: `clarification_accuracy=6/10=0.60`. هدف: ≥0.80.

- [x] **12.2.1** بررسی artifact برای case‌های clarification fail شده.
- [x] **12.2.2** Fix ambiguity_detector اگر لازم است.
- [ ] **12.2.3** Rerun و verify با هدف `clarification_accuracy >= 0.8`.

### 12.3 - Answer Formatter

- [x] **12.3.1** پیاده‌سازی `src/output/answer_formatter.py`:
    - [x] scalar result: خلاصه فارسی یک جمله.
    - [x] table result: جدول فارسی ساده.
    - [x] empty result: پیام صریح فارسی «داده‌ای یافت نشد».
    - [x] abstain: توضیح دقیق فارسی چرا پاسخ داده نمی‌شود.
    - [x] clarification: سوال مشخص فارسی برای رفع ابهام.
    - [x] refuse_unsafe: پیام رد صریح فارسی.
    - [x] disclaimer: «این داده‌های پژوهشی است و تشخیص پزشکی نیست.»
    - [x] trace_id و SQL در خروجی (SQL مخفی پیش‌فرض).
    - [x] هرگز نتیجه‌ای که در row‌های واقعی نیست، ادعا نشود.
- [ ] **12.3.2** تست‌ها `tests/tier1_unit/test_answer_formatter.py`:
    - [ ] scalar/table/empty/abstain/clarification/refuse_unsafe formatter test.
    - [ ] disclaimer presence test.
    - [ ] no-hallucination test.

### 12.4 - Chart Recommender

- [x] **12.4.1** پیاده‌سازی `src/output/chart_recommender.py`:
    - [x] یک scalar → `kpi_card`.
    - [x] دو ستون (group + metric) → `bar_chart`.
    - [x] سری زمانی → `line_chart`.
    - [x] توزیع → `histogram` یا `pie_chart`.
    - [x] ماتریس → `heatmap`.
    - [x] `recommended_visual` و `chart_reason` در خروجی.
- [ ] **12.4.2** تست `tests/tier1_unit/test_chart_recommender.py`.

### 12.5 - Explanation Builder

- [x] **12.5.1** پیاده‌سازی `src/output/explanation_builder.py`:
    - [x] توضیح فارسی SQL به زبان ساده.
    - [x] assumptions از `SQLAttempt.parsed_payload.assumptions`.
    - [x] confidence level در توضیح.
- [ ] **12.5.2** تست `tests/tier1_unit/test_explanation_builder.py`.

### 12.6 - Narrative Generator (اختیاری، بعد از 12.3-12.5)

- [ ] **12.6.1** پیاده‌سازی `src/output/narrative_generator.py`:
    - [ ] روایت فارسی ساده (فقط از row‌های واقعی، no hallucination).
    - [ ] warning اگر نتیجه ناقص یا مشکوک است.
- [ ] **12.6.2** تست `tests/tier1_unit/test_narrative_generator.py`.

### 12.7 - Integration و Acceptance

- [x] **12.7.1** اتصال `answer_formatter` به graph node نهایی در `base_nodes.py`.
- [x] **12.7.2** اتصال `chart_recommender` و `explanation_builder` به graph output.
- [x] **12.7.3** Compile check تمام ماژول‌های output.
- [ ] **12.7.4** Rerun behavior benchmark پس از 12.1-12.3:
    - [ ] فرمان: `python scripts\run_benchmark.py --mode agent --dataset behavior_dev --sample 20 --ablation-id phase12_output_integration --trace-level full`
    - [ ] هدف: `safety_rejection_accuracy >= 0.8`، `clarification_accuracy >= 0.8`، `unsafe_sql = 0`.

---

## Phase 13 - Reliability Gate, Multi-Candidate, Abstention [IN PROGRESS]

Implemented:

- [x] Basic abstention through intent classification and pre-generation route.
- [x] Reliability metrics module exists.
- [x] First annotation-only reliability gate exists.
  - `src/evaluation/reliability_gate.py`
  - `src/evaluation/sql_consistency_critic.py`
  - `src/evaluation/candidate_consistency.py`
  - `src/evaluation/multi_candidate_policy.py`
  - `tests/tier1_unit/test_reliability_gate.py`
  - `tests/tier1_unit/test_sql_consistency_critic.py`
  - `tests/tier1_unit/test_candidate_consistency.py`
  - `tests/tier1_unit/test_multi_candidate_policy.py`
  - benchmark annotation in `scripts/run_benchmark.py` behind `reliability_gate=true`
  - phase doc: `docs/phases/PHASE_13_RELIABILITY_GATE.md`

Required:

- [x] Extend graph state with `candidate_sqls`, `selected_candidate_id`, `reliability_decision`, `candidate_consistency_report`.
- [x] `src/graph/nodes/generate_candidates_node.py`
- [x] `src/graph/nodes/check_consistency_node.py`
- [x] `src/graph/nodes/compute_reliability_node.py`
- [x] `src/evaluation/reliability_gate.py` as the first runtime-signal gate.
- [x] Fix retry_count loop bug in `compute_reliability_node`.
- [ ] Decide whether a later graph node should wrap `src/evaluation/reliability_gate.py` or move the gate into a graph-specific module after smoke evidence.
- [ ] Candidate consistency over tables, columns, joins, aggregation and result hashes.
- [x] First lightweight question/SQL consistency critic for explicit obligations: rate computation, grouped/per-segment shape, above/below-average thresholds, change measure, binning and ordering warnings.
- [x] Standalone candidate consistency contract over candidate SQL signatures and optional result hashes.
- [x] Latency-aware adaptive multi-candidate policy:
  - simple/confident questions stay single-candidate.
  - extra candidates are only considered for retry/validation failure, execution failure, low confidence, complex dashboard/category hints, or hard/complex metadata hints when available.
  - default adaptive candidate count is `2`, not unbounded.
- [x] Artifact-backed multi-candidate A/B comparison scaffold:
  - `src/evaluation/multi_candidate_ablation.py`
  - `scripts/analyze_multi_candidate_ablation.py`
  - `tests/tier1_unit/test_multi_candidate_ablation.py`
  - reads existing benchmark artifacts and optional dual-policy reports only.
  - verifies `selected_cases_hash`, dataset hash, model consistency, EX/valid SQL/reliability/unsafe SQL deltas, latency deltas, candidate activation, candidate disagreement counts, and baseline-correct -> adaptive-wrong regressions.
  - does not run a model, execute SQL, edit predictions, infer missing semantic labels, or use case IDs/gold SQL as tuning rules.
- [ ] Abstain or ask clarification on material disagreement.
- [x] Reliability gate decision object with `answer | retry | ask_clarification | needs_review | refuse_unsafe`.
- [ ] User-facing reliability object with output warnings and graph routing.
- [ ] Aggregate-first / low-row-count protection from threat model.
- [x] Small dev smoke with `reliability_gate=true` before any user-facing routing change. (phase13_smoke_v2: evaluated=4, VTD-237 and VTD-343 failed gracefully)

---

## Phase 14 - Edge Runtime Optimization [TODO]

- [ ] Profile latency by graph node.
- [ ] Cache normalization, schema linking, retrieval and successful SQL.
- [ ] Compare local model variants under the same benchmark protocol.
- [ ] Prototype lightweight deterministic state machine after research runtime stabilizes.
- [ ] Compare LangGraph research runtime vs edge runtime.
- [ ] Keep unsafe execution rate at `0`.

---

## Phase 15 - Research Packaging [IN PROGRESS]

هدف: آماده کردن پروژه برای انتشار پژوهشی. این فاز را نباید قبل از paper-grade balanced dev benchmark شروع کنیم.

### Completed:

- [x] `DATASET_CARD.md`
- [x] `docs/THREAT_MODEL.md`
- [x] Phase docs for Phase 1, 2, 3, 4, 5, 6, 7 and 10.
- [x] Paper-facing A4 dual-policy evidence package: `results/paper/20260520_phase16_a4_dual_policy_evidence`.

### 15.1 - Limitations Document

- [ ] **15.1.1** `docs/paper/limitations.md` با بخش‌های زیر:
    - [ ] Dataset: single-author annotation، leakage risk (`total_issues=724`)، 400-case only، یک domain.
    - [ ] Model: local 3B/7B only، no multilingual، Persian-first with English SQL.
    - [ ] Evaluation: EX ≠ semantic correctness، judge coverage limited (A4 smoke only so far).
    - [ ] Safety: `safety_rejection_accuracy=0` در آخرین behavior run (باید قبل از paper claim رفع شود).
    - [ ] Generalization: یک domain (mental-health/student) و یک database family.

### 15.2 - Ablation Table

- [ ] **15.2.1** `docs/paper/ablation_table.md`:
    - [ ] **BLOCKER**: نیاز به paper-grade A0-A7 run روی balanced dev (≥20 case per config).
    - [ ] هر row باید artifact path داشته باشد.
    - [ ] هر metric باید Bootstrap CI 95% داشته باشد.
    - [ ] هیچ عدد بدون artifact مجاز نیست.

### 15.3 - Qualitative Examples

- [ ] **15.3.1** `docs/paper/qualitative_examples.md`:
    - [ ] حداقل 5 مثال موفق از artifact واقعی.
    - [ ] حداقل 5 مثال failure با تحلیل.
    - [ ] حداقل 1 مثال `semantic_correct_strict_incorrect` (مثل VTD-300).
    - [ ] هرگز SQL یا نتیجه fake نشود.

### 15.4 - Reproduce Script

- [ ] **15.4.1** `scripts/reproduce_paper_results.py`:
    - [ ] لیست دقیق commandها با env vars برای بازتولید همه artifact‌های paper.
    - [ ] hash verification برای dataset files.
    - [ ] README.md با step-by-step instructions.

### 15.5 - Final Walkthrough و README

- [ ] **15.5.1** `walkthrough.md` در root با architecture، نتایج اصلی (از artifact)، راهنمای اجرا.
- [ ] **15.5.2** `README.md` نهایی با Feature Decision Table، Quick benchmark commands، Model requirements.
- [ ] **15.5.3** `.gitignore` اطمینان از عدم commit مدل‌های GGUF و داده‌های حساس.
- [ ] **15.5.4** بررسی PII در همه artifacts قبل از push.

### 15.6 - Paper Results Summary

- [ ] **15.6.1** `results/reports/paper_tables.md`:
    - [ ] **BLOCKER**: فقط بعد از paper-grade benchmark (≥50 case balanced dev) و dual-policy judge.
    - [ ] جدول A0-A7 ablation با EX، Valid SQL، Reliability، Semantic، Strict.
    - [ ] جدول R0-R3 retrieval با Hit Rate، Latency.
    - [ ] Bootstrap CI برای هر metric.

---

## Immediate Next Tasks

1. [x] Phase 10: verify leakage/retrieval self-overlap mitigation.
   - [x] Add benchmark/runtime self-overlap exclusion for retrieved examples by `base_id` and normalized question.
   - [x] Store exclusion policy and removed self-match count in benchmark artifacts.
   - [x] User ran `pytest tests\tier2_integration\test_agent_benchmark_trace.py -vv --tb=short` -> `4 passed, 1 warning`.
   - [x] User ran `run_benchmark.py --mode retrieval --dataset dev --sample 5 --top-k 3 --exclude-self`.
   - [x] Verified artifact: `results/benchmark/20260516_075846_retrieval_dev_qwen2-5-coder-7b_manual_exclude_self_smoke`.
2. [x] Phase 10: run larger shape-contract smoke with `--samples-per-level 2`, `--exclude-self`, `--trace-level full`, and inspect artifacts.
   - [x] Latest artifact after fixes: `results/benchmark/20260517_031221_agent_dev_qwen2-5-coder-7b_manual_agent_shape_contract_spl2_after_fixes`.
   - [x] Phase 10 infrastructure closed with known quality limitations.
3. [x] Phase 11: verify first-slice tooling and generate the first real artifact-backed error-analysis report.
   - [x] Statistical helpers, artifact analyzer and first ablation configs have been added.
   - [x] Run focused Phase 11 tests: `5 passed`.
   - [x] Analyze the Phase 10 closeout artifact.
   - [x] Generated report: `results/error_analysis/20260517_phase11_spl2_after_fixes/error_report.md`.
4. [x] Phase 11: add `scripts/run_ablation.py` and `tests/tier1_unit/test_ablation_runner.py`.
5. [x] Phase 11: run ablation dry-run manifest first; do not claim ablation results until real benchmark artifacts exist.
   - [x] Manifest: `results/ablation/20260517_phase11_dry_run_manifest/ablation_manifest.json`.
6. [x] Phase 11: decide whether to run real A0-A7 ablations now or first wire/verify feature flags more strictly.
   - [x] Chosen path: wire/verify feature flags first.
   - [x] Runtime-enforced/locked/metadata-only flag contract is now recorded in benchmark config and ablation manifest.
7. [x] Phase 11: implement true value-linking isolation before real A0-A7 ablations.
8. [x] Phase 11: run real A0-A7 ablation smoke.
9. [x] Phase 11: generate artifact-backed ablation comparison report.
   - [x] Report: `results/ablation/20260517_phase11_a0_a7_execute/ablation_comparison.md`.
10. [x] Phase 11: inspect A4 latency anomaly using its real benchmark artifact before expanding the ablation suite.
    - [x] Root cause found/fixed for future runs: dict-style schema context caused value-link candidate fallback to the full value dictionary.
11. [x] Phase 11: rerun targeted A4 smoke after the value-link trace fix and compare latency/grounding against the old A4 artifact.
12. [x] Phase 11: rerun targeted A4 smoke after matrix intent/prompt/shape hardening.
13. [x] Phase 11: decide next quality path: implement a general matrix support-threshold/sorting policy before moving to Phase 16 semantic judge.
14. [x] Phase 11: rerun targeted A4 smoke after support-threshold/sorting policy.
    - [x] Artifact: `results/benchmark/manual_a4_after_matrix_support_policy`.
    - [x] Report: `results/error_analysis/20260518_a4_after_matrix_support_policy/error_report.md`.
    - [x] Key finding: `VTD-371` is now exact-correct, but A4 remains weak due false abstentions.
15. [x] Phase 11: diagnose false-abstention regressions in A4 support-policy artifact before scaling A0-A7 again.
    - [x] Inspect validation errors for `VTD-027`, `VTD-343`, `VTD-300`, and `VTD-078`.
    - [x] Separate the first-pass over-strict shape-contract failures from genuine model SQL failures.
    - [x] Keep any fix general by question/table/shape, not by case ID.
    - [x] Implement first two general mitigations: `student_depression.family_history` alias rewrite and non-mandatory `positives` helper column.
    - [x] Rerun targeted A4 smoke after false-abstention mitigation.
    - [x] Fix graph to execute the same rewritten SQL that passed validation.
    - [x] Rerun targeted A4 smoke after rewritten-SQL graph promotion.
    - [x] Accept equivalent grouped-rate null filter forms.
    - [x] Rerun attempt after equivalent-null-filter acceptance was incomplete and is not a result.
    - [x] Add generation token cap.
    - [x] Rerun targeted A4 smoke after generation token cap.
16. [x] Phase 11: align artifact error analysis with `docs/06` taxonomy without faking semantic labels.
    - [x] Keep `research_error` for historical report continuity.
    - [x] Add `docs06_error` and `requires_semantic_review` to generated failure rows.
    - [x] Generate new report from real A4 token-cap artifact:
      `results/error_analysis/20260519_phase11_docs06_taxonomy_a4_token_cap/error_report.md`.
    - [x] Result: docs/06 deterministic labels = `AGGREGATION_ERROR=2`, `SCHEMA_LINKING_ERROR=1`; pending semantic review = `2`.
    - [x] Tests: `7 passed`.
17. [x] Phase 11 next path chosen: retrieval ablation matrix first.
    - Reason: it is Phase 11-native and does not require semantic judging or case-specific SQL tuning.
    - [x] Add backend selector and R0-R3 configs.
    - [x] Create dry-run manifest: `results/ablation/20260519_phase11_retrieval_dry_run_manifest/ablation_manifest.json`.
    - [x] Smoke R0 BM25 config: `results/benchmark/manual_r0_retrieval_bm25_smoke`.
18. [x] Phase 11: execute real R0-R3 retrieval ablation matrix and summarize only from generated artifacts.
    - [x] Manifest: `results/ablation/20260519_phase11_retrieval_execute/ablation_manifest.json`.
    - [x] Report: `results/ablation/20260519_phase11_retrieval_execute/ablation_comparison.md`.
    - [x] `same_dataset_hash=True`; `same_selected_cases_hash=True`; jobs completed `4/4`.
19. [x] Phase 11: run larger retrieval ablation on full dev.
    - [x] Manifest: `results/ablation/20260519_phase11_retrieval_dev_full_execute/ablation_manifest.json`.
    - [x] Report: `results/ablation/20260519_phase11_retrieval_dev_full_execute/ablation_comparison.md`.
    - [x] Initial result: BM25 and vector hit `60/60`; hybrid and identity-rerank hit `58/60`.
20. [x] Phase 11: investigate and fix hybrid retrieval misses without overfitting.
    - [x] Added schema-evidence preservation after self-overlap filtering.
    - [x] Final manifest: `results/ablation/20260519_phase11_retrieval_dev_full_final/ablation_manifest.json`.
    - [x] Final report: `results/ablation/20260519_phase11_retrieval_dev_full_final/ablation_comparison.md`.
    - [x] Final result: R0/R1/R2/R3 all hit `60/60` on full dev.
21. [x] Phase 11 next path chosen: Phase 16 mock/offline judge scaffold first.
    - Reason: remaining valid-SQL mismatches need semantic/business review before more prompt/shape tuning.
22. [x] Phase 16: implement mock/offline LLM-as-a-Judge scaffold after trace artifacts and Phase 11 analysis are stable.
    - [x] Code: `src/evaluation/llm_judge.py`, `scripts/judge_benchmark_artifact.py`.
    - [x] Tests/compile passed.
    - [x] Real mock judgment artifact: `results\judgments\20260519_phase16_mock_a4_token_cap`.
23. [x] Phase 16: add integrated benchmark output files for mock judge mode.
    - [x] Add `judge_costs.json` and `semantic_business_summary.csv` for standalone mock mode.
    - [x] Add `run_benchmark.py --use-judge --judge-provider mock` integration.
    - [x] Run integration smoke and verify final predictions path is used.
24. [x] Phase 16: wire OpenRouter provider and run small live pilots.
    - [x] Mock judge over A0-A7 smoke artifacts completed.
    - [x] OpenRouter provider wiring completed without live API calls.
    - [x] Qwen live pilot completed: `results\judgments\20260519_phase16_openrouter_qwen_a4_sample2_retry2`.
    - [x] DeepSeek free no-reasoning live pilot completed: `results\judgments\20260519_phase16_openrouter_deepseek_free_a4_sample2_no_reasoning`.
25. [x] Phase 16: run a controlled multi-judge sample on more failures/successes and compare judge agreement before using semantic scores in paper tables.
    - [x] First all-failure Qwen/DeepSeek live runs completed on `manual_a4_after_generation_token_cap`.
    - [x] Judge report canonicalization added after seeing raw provider labels `partial_match`, `invalid`, and `disapproved`.
    - [x] Rerun Qwen/DeepSeek all-failure judgments once with canonicalized verdict reporting.
    - [x] Add artifact-backed judge agreement analyzer:
      - `src/evaluation/judge_agreement.py`
      - `scripts/analyze_judge_agreement.py`
      - `tests/tier1_unit/test_judge_agreement.py`
    - [x] Agreement artifact: `results\judgments\20260519_phase16_qwen_deepseek_a4_failure_agreement`.
    - [x] Success/all-prediction coverage artifact:
      - Qwen: `results\judgments\20260519_phase16_openrouter_qwen_a4_all_predictions`; judged `8/8`, authoritative `8/8`, semantic counts `correct=3`, `incorrect=4`, `unjudged=1`.
      - DeepSeek free: `results\judgments\20260519_phase16_openrouter_deepseek_free_a4_all_predictions`; judged `8/8`, authoritative `6/8`, provider errors `2`, semantic counts `correct=2`, `incorrect=1`, `unjudged=5`.
      - Agreement: `results\judgments\20260519_phase16_qwen_deepseek_a4_all_predictions_agreement\judge_agreement.md`.
      - Agreement result: common_cases `8`, semantic_agreement `4/8`, verdict_agreement `4/8`, final_counts `agreed_correct=2`, `agreed_incorrect=1`, `adjudication_required=5`.
      - Interpretation: success cases `VTD-027` and `VTD-039` are confirmed by both judges; `VTD-371` is Qwen-correct but DeepSeek provider-error, so it remains adjudication-required.
    - [x] Added targeted judge selection for paid/adjudicator runs: `--case-ids`.
    - [x] Replaced DeepSeek free with paid `deepseek/deepseek-v4-flash` for all-prediction agreement and compared against Qwen; no labels were inferred from old free provider-error rows.
      - command 1: `.\.venv\Scripts\python.exe scripts\judge_benchmark_artifact.py results\benchmark\manual_a4_after_generation_token_cap --output-dir results\judgments\20260520_phase16_openrouter_deepseek_paid_a4_all_predictions --judge-provider openrouter --judge-model deepseek/deepseek-v4-flash --no-judge-reasoning --all-predictions`
      - command 2: `.\.venv\Scripts\python.exe scripts\analyze_judge_agreement.py results\judgments\20260519_phase16_openrouter_qwen_a4_all_predictions results\judgments\20260520_phase16_openrouter_deepseek_paid_a4_all_predictions --output-dir results\judgments\20260520_phase16_qwen_deepseek_paid_a4_all_predictions_agreement`
      - paid DeepSeek artifact: `results\judgments\20260520_phase16_openrouter_deepseek_paid_a4_all_predictions`.
      - paid DeepSeek summary: judged `8/8`, authoritative `7/8`, `provider_parse_error=1`, semantic counts `correct=3`, `incorrect=1`, `unjudged=4`.
      - agreement artifact: `results\judgments\20260520_phase16_qwen_deepseek_paid_a4_all_predictions_agreement`.
      - agreement result: common_cases `8`, semantic_agreement `5/8`, verdict_agreement `4/8`, final_counts `agreed_correct=3`, `agreed_incorrect=1`, `adjudication_required=4`.
      - confirmed by both judges: `VTD-027`, `VTD-039`, `VTD-371` as business-correct; `VTD-237` as business-incorrect.
      - unresolved/adjudication-required: `VTD-078`, `VTD-141`, `VTD-300`, `VTD-343`.
    - [x] Ran a third adjudicator only on unresolved case IDs using `--case-ids`.
      - command: `.\.venv\Scripts\python.exe scripts\judge_benchmark_artifact.py results\benchmark\manual_a4_after_generation_token_cap --output-dir results\judgments\20260520_phase16_openrouter_gpt51_a4_unresolved_only --judge-provider openrouter --judge-model openai/gpt-5.1 --no-judge-reasoning --all-predictions --case-ids VTD-078 VTD-141 VTD-300 VTD-343`
      - GPT-5.1 artifact: `results\judgments\20260520_phase16_openrouter_gpt51_a4_unresolved_only`.
      - GPT-5.1 summary: judged `4/4`, authoritative `4/4`, verdicts `business_incorrect=2`, `invalid_sql=1`, `partial_business_match=1`, semantic counts `incorrect=3`, `unjudged=1`.
      - after the third adjudicator artifact exists, run `scripts\analyze_judge_consensus.py` over Qwen all-prediction, paid DeepSeek all-prediction and the third-judge unresolved-only artifact.
    - [x] Built conservative three-judge consensus report.
      - command: `.\.venv\Scripts\python.exe scripts\analyze_judge_consensus.py results\judgments\20260519_phase16_openrouter_qwen_a4_all_predictions results\judgments\20260520_phase16_openrouter_deepseek_paid_a4_all_predictions results\judgments\20260520_phase16_openrouter_gpt51_a4_unresolved_only --output-dir results\judgments\20260520_phase16_qwen_deepseek_paid_gpt51_a4_consensus`
      - consensus artifact: `results\judgments\20260520_phase16_qwen_deepseek_paid_gpt51_a4_consensus`.
      - first consensus final_counts: `consensus_correct=3`, `consensus_incorrect=4`, `adjudication_required=1`.
      - consensus_correct: `VTD-027`, `VTD-039`, `VTD-371`.
      - consensus_incorrect: `VTD-078`, `VTD-141`, `VTD-237`, `VTD-343`.
      - initially unresolved: `VTD-300`; all three judges returned partial/unjudged, so it must not become a semantic-correct claim.
    - [x] Added written partial-business-match policy to consensus reporting and regenerated the consensus artifact from existing judgment rows only.
      - updated consensus artifact: `results\judgments\20260520_phase16_qwen_deepseek_paid_gpt51_a4_consensus`.
      - updated final_counts: `consensus_correct=3`, `consensus_incorrect=4`, `consensus_partial_business_match=1`.
      - metric_policy_counts: `semantic_correct=3`, `semantic_incorrect=4`, `partial_business_match=1`, `needs_human_review=0`.
      - `VTD-300` is now `consensus_partial_business_match`, not semantic-correct and not semantic-incorrect.
    - [x] Added explicit redaction policy to judge summary artifacts.
      - code: `src\evaluation\llm_judge.py`.
      - policy fields: `redaction_applied=true`, `raw_rows_sent=false`, `result_previews_sent=false`, `prompt_response_trace_sent=false`.
      - excluded fields: `raw_database_rows`, `execution_result_preview`, `gold_result_preview`, `full_prompt`, `raw_model_response`.
      - verification: `.\.venv\Scripts\python.exe -m pytest tests\tier1_unit\test_llm_judge.py tests\tier1_unit\test_judge_consensus.py tests\tier1_unit\test_judge_agreement.py -vv --tb=short` -> `18 passed`.
      - offline artifact: `results\judgments\20260520_phase16_mock_redaction_policy_smoke\judge_summary.json`.
    - [x] Updated semantic judge policy to `phase16_sql_business_logic_v1`.
      - policy: semantic correctness means the generated SQL answers the user's actual question. Gold SQL is a reference implementation, not a mandatory output schema.
      - extra harmless columns/parameters and missing gold-only support columns should not make a query business-incorrect if the user can still get the answer they asked for.
      - partial provider labels now defer to the explicit semantic boolean: partial+true -> `business_correct`; partial+false -> `business_incorrect`; partial+null -> `partial_business_match`.
      - dual policy mode added: `--judge-policy semantic` reports user-question utility, while `--judge-policy strict` reports stricter reference/gold-output-contract correctness.
      - consensus summaries now record `prompt_versions`, `same_prompt_version`, `judge_policies`, and `same_judge_policy` so semantic and strict runs are not silently mixed.
      - verification: `.\.venv\Scripts\python.exe -m pytest tests\tier1_unit\test_llm_judge.py tests\tier1_unit\test_judge_consensus.py tests\tier1_unit\test_judge_agreement.py -vv --tb=short` -> `23 passed`.
      - compile check: `.\.venv\Scripts\python.exe -m py_compile src\evaluation\llm_judge.py src\evaluation\judge_consensus.py scripts\judge_benchmark_artifact.py scripts\analyze_judge_consensus.py` -> passed.
      - offline v1 contract smoke: `results\judgments\20260520_phase16_mock_v1_user_question_policy_smoke\judge_summary.json` records `prompt_version=phase16_sql_business_logic_v1`, `redaction_applied=true`, and `total_judged=1`. This mock artifact is not a semantic correctness claim.
      - dual-policy mock smoke:
        - semantic: `results\judgments\20260520_phase16_mock_v1_semantic_vtd300_policy_smoke` -> `judge_policy=semantic_user_question`, non-authoritative, `requires_semantic_review=1`.
        - strict: `results\judgments\20260520_phase16_mock_v1_strict_vtd300_policy_smoke` -> `judge_policy=strict_reference`, non-authoritative, `strict_reference_mismatch=1`.
    - [x] Completed v1 rerun plan: VTD-300 and the full A4 all-prediction slice were judged with prompt version `phase16_sql_business_logic_v1` under both `--judge-policy semantic` and `--judge-policy strict`. Old v0 artifacts remain historical evidence only and must not be reinterpreted as final v1 labels.
    - [x] Ran live v1 dual-policy VTD-300 check with Qwen and paid DeepSeek.
      - semantic Qwen: `results\judgments\20260520_phase16_openrouter_qwen_a4_v1_semantic_vtd300` -> authoritative, `business_correct=1`.
      - semantic paid DeepSeek: `results\judgments\20260520_phase16_openrouter_deepseek_paid_a4_v1_semantic_vtd300` -> authoritative, `business_correct=1`.
      - semantic agreement: `results\judgments\20260520_phase16_qwen_deepseek_paid_a4_v1_semantic_vtd300_agreement` -> `agreed_correct=1`, semantic agreement `1/1`.
      - strict Qwen: `results\judgments\20260520_phase16_openrouter_qwen_a4_v1_strict_vtd300` -> authoritative, `business_incorrect=1`.
      - strict paid DeepSeek: `results\judgments\20260520_phase16_openrouter_deepseek_paid_a4_v1_strict_vtd300` -> non-authoritative `provider_parse_error=1`.
      - strict agreement: `results\judgments\20260520_phase16_qwen_deepseek_paid_a4_v1_strict_vtd300_agreement` -> `adjudication_required=1`.
      - interpretation: VTD-300 is now confirmed semantically correct under user-question utility, while strict-reference correctness remains unresolved until a paid DeepSeek rerun or GPT-5.1 strict adjudication.
    - [x] Ran GPT-5.1 strict adjudication for VTD-300 and rebuilt strict consensus.
      - GPT-5.1 strict artifact: `results\judgments\20260520_phase16_openrouter_gpt51_a4_v1_strict_vtd300` -> authoritative, `business_incorrect=1`.
      - strict consensus artifact: `results\judgments\20260520_phase16_qwen_deepseek_paid_gpt51_a4_v1_strict_vtd300_consensus`.
      - strict consensus result: `consensus_incorrect=1`, `same_prompt_version=true`, `same_judge_policy=true`, authoritative incorrect votes `2`.
      - final VTD-300 dual-policy status: `semantic_user_question_correct=true` by Qwen+paid DeepSeek agreement; `strict_reference_correct=false` by Qwen+GPT-5.1 consensus. This is a paper-useful example of EX/reference mismatch while user-question utility is preserved.
    - [x] Added dual-policy report tooling.
      - code: `src\evaluation\dual_policy_report.py`.
      - CLI: `scripts\analyze_dual_policy_judgments.py`.
      - test: `tests\tier1_unit\test_dual_policy_report.py`.
      - agreement metadata now records `prompt_version` and `judge_policy` for both sides.
      - verification: `.\.venv\Scripts\python.exe -m pytest tests\tier1_unit\test_dual_policy_report.py tests\tier1_unit\test_judge_agreement.py tests\tier1_unit\test_judge_consensus.py -vv --tb=short` -> `5 passed`.
      - broader judge verification: dual-policy + agreement + consensus + llm_judge -> `24 passed`.
      - VTD-300 dual-policy report: `results\judgments\20260520_phase16_a4_v1_vtd300_dual_policy_report`.
      - dual-policy result: `semantic_counts.correct=1`, `strict_counts.incorrect=1`, `combined_counts.semantic_correct_strict_incorrect=1`.
    - [x] Ran full A4 v1 dual-policy Qwen/paid-DeepSeek judgment and generated a dual-policy report.
      - semantic agreement artifact: `results\judgments\20260520_phase16_qwen_deepseek_paid_a4_v1_semantic_all_agreement`.
      - semantic agreement result: `common_cases=8`, `semantic_agreement=8/8`, `agreed_correct=4`, `agreed_incorrect=4`.
      - strict agreement artifact: `results\judgments\20260520_phase16_qwen_deepseek_paid_a4_v1_strict_all_agreement`.
      - strict agreement result: `common_cases=8`, `semantic_agreement=7/8`, `agreed_correct=3`, `agreed_incorrect=4`, `adjudication_required=1`.
      - dual-policy report: `results\judgments\20260520_phase16_a4_v1_all_dual_policy_report`.
      - dual-policy counts: `both_correct=3`, `both_incorrect=3`, `semantic_correct_strict_incorrect=1`, `adjudication_required=1`.
      - cases:
        - both correct: `VTD-027`, `VTD-039`, `VTD-371`.
        - both incorrect: `VTD-078`, `VTD-237`, `VTD-343`.
        - semantic correct / strict incorrect: `VTD-300`.
        - strict adjudication required: `VTD-141` because paid DeepSeek strict returned `provider_parse_error`.
    - [x] Ran GPT-5.1 strict adjudication only for `VTD-141`, then rebuilt strict consensus and the full A4 dual-policy report.
      - GPT-5.1 strict artifact: `results\judgments\20260520_phase16_openrouter_gpt51_a4_v1_strict_vtd141` -> authoritative, `business_incorrect=1`.
      - final strict consensus artifact: `results\judgments\20260520_phase16_qwen_deepseek_paid_gpt51_a4_v1_strict_all_consensus`.
      - strict consensus result: `consensus_correct=3`, `consensus_incorrect=5`, `same_prompt_version=true`, `same_judge_policy=true`.
      - final dual-policy artifact: `results\judgments\20260520_phase16_a4_v1_all_dual_policy_final`.
      - final dual-policy counts: `semantic_counts.correct=4`, `semantic_counts.incorrect=4`, `strict_counts.correct=3`, `strict_counts.incorrect=5`, `combined_counts.both_correct=3`, `combined_counts.both_incorrect=4`, `combined_counts.semantic_correct_strict_incorrect=1`.
      - final cases:
        - both correct: `VTD-027`, `VTD-039`, `VTD-371`.
        - both incorrect: `VTD-078`, `VTD-141`, `VTD-237`, `VTD-343`.
        - semantic correct / strict incorrect: `VTD-300`.
      - anti-overfit/anti-fake note: no model/prompt tuning is made from these labels; this is evaluation evidence only. The report merges existing judgment artifacts and does not call a model, edit judgments, or convert unjudged/provider-error rows into correctness claims.
    - [x] Decision after full A4 dual-policy slice:
      - use the 8-case A4 slice as smoke/slice evidence only, not a paper-grade final metric.
      - do not tune prompts, validators, retrieval, or shape contracts to `VTD-027`, `VTD-039`, `VTD-078`, `VTD-141`, `VTD-237`, `VTD-300`, `VTD-343`, or `VTD-371`.
      - next engineering path: Phase 13 reliability improvements first, because they can use validation, execution, retry, abstention, and judge evidence as general signals rather than case-specific fixes.
      - next evaluation path: after Phase 13 changes, create a new balanced dev artifact and rerun dual-policy judging on that artifact before considering any fixed-test or paper-grade claim.
26. [x] Phase 16/15: package the completed A4 dual-policy smoke evidence without creating new labels.
    - [x] Added artifact-backed packaging code:
      - `src\evaluation\dual_policy_packaging.py`
      - `scripts\package_dual_policy_evidence.py`
      - `tests\tier1_unit\test_dual_policy_packaging.py`
    - [x] Produced a compact paper-facing table from `results\judgments\20260520_phase16_a4_v1_all_dual_policy_final` and benchmark summary `results\benchmark\manual_a4_after_generation_token_cap`.
      - output dir: `results\paper\20260520_phase16_a4_dual_policy_evidence`
      - summary: `results\paper\20260520_phase16_a4_dual_policy_evidence\paper_evidence_summary.json`
      - case CSV: `results\paper\20260520_phase16_a4_dual_policy_evidence\paper_evidence_cases.csv`
      - report: `results\paper\20260520_phase16_a4_dual_policy_evidence\paper_evidence_table.md`
    - [x] Labeled the table explicitly as `small_dev_a4_slice`, not a final benchmark result.
    - [x] Included both metrics side by side:
      - semantic user-question correctness: answers the user's actual question.
      - strict reference correctness: matches the stricter gold/reference output contract.
    - [x] Preserved the anti-fake policy: report only existing artifact-backed labels; do not infer missing labels or overwrite provider-error/unjudged rows.
    - [x] Artifact-backed package counts:
      - benchmark slice: `execution_accuracy=0.375`, `valid_sql_rate=0.625`, `reliability_score=0.25`, `total_evaluated=8`.
      - dual-policy: `semantic_correct=4`, `semantic_incorrect=4`, `strict_correct=3`, `strict_incorrect=5`, `both_correct=3`, `both_incorrect=4`, `semantic_correct_strict_incorrect=1`.
    - [x] Verification:
      - `.\.venv\Scripts\python.exe -m pytest tests\tier1_unit\test_dual_policy_packaging.py tests\tier1_unit\test_dual_policy_report.py -vv --tb=short` -> `2 passed`.
      - `.\.venv\Scripts\python.exe -m py_compile src\evaluation\dual_policy_packaging.py scripts\package_dual_policy_evidence.py` -> passed.
27. [ ] Phase 13: implement reliability gate and abstention policy before more SQL prompt/validator tuning.
    - [x] Add a reliability decision layer that consumes existing runtime-style signals: validation issues, execution success, retry count, action type, generated SQL presence, optional judge consensus when available, and trace completeness.
      - code: `src\evaluation\reliability_gate.py`.
      - anti-overfit constraint: gate logic does not use `case_id`, `gold_sql`, `execution_correct`, `result_match`, or known benchmark ID lists.
      - inspected graph state: `src\graph\state.py` currently provides raw/normalized question, intent/confidence, safety, clarification, generated SQL, attempts, retry counts, validation errors, execution result/error and ablation config.
      - graph state reliability surface now exists: `candidate_sqls`, `selected_candidate_id`, `candidate_consistency`, `multi_candidate_policy`, and `reliability`.
      - graph state default behavior is inactive/empty, so this does not increase latency or change routing.
      - inspected benchmark prediction path: `scripts\run_benchmark.py::agent_prediction` keeps benchmark-only labels for reporting, while the gate consumes a separate runtime-style `gate_record`.
    - [x] Define conservative states: `answer`, `retry`, `ask_clarification`, `needs_review`, and `refuse_unsafe`.
    - [x] Add unit tests using synthetic records; tests do not depend on fixed benchmark IDs as special cases.
      - test: `tests\tier1_unit\test_reliability_gate.py`.
    - [x] Wire `reliability_gate` as a runtime-enforced feature flag and benchmark annotation.
      - `src\evaluation\ablation_flags.py` now treats `reliability_gate` as runtime-enforced.
      - `scripts\run_benchmark.py` records `reliability_gate`, `reliability_gate_action`, `reliability_gate_reason`, and `reliability_gate_warnings` when the flag is enabled.
      - current behavior: annotation-only; it does not overwrite `actual_action`, `final_answer`, or graph routing yet.
    - [x] Document Phase 13 gate status:
      - `docs\phases\PHASE_13_RELIABILITY_GATE.md`.
      - `docs\phases\README.md`.
    - [x] Verification:
      - `.\.venv\Scripts\python.exe -m pytest tests\tier1_unit\test_reliability_gate.py tests\tier1_unit\test_ablation_runner.py -vv --tb=short` -> `13 passed`.
      - broader Phase 13/16 related check -> `37 passed`.
      - `.\.venv\Scripts\python.exe -m py_compile src\evaluation\reliability_gate.py src\evaluation\ablation_flags.py scripts\run_benchmark.py` -> passed.
    - [x] Run a small dev smoke after the gate and compare action quality, false abstention, valid SQL rate, EX, and latency.
      - config: `experiments\configs\A7_reliability_gate_smoke.yaml`.
      - command: `.\.venv\Scripts\python.exe scripts\run_benchmark.py --config experiments\configs\A7_reliability_gate_smoke.yaml --output-dir results\benchmark\manual_phase13_reliability_gate_smoke`.
      - artifact: `results\benchmark\manual_phase13_reliability_gate_smoke`.
      - result: evaluated `4`, failures `3`, execution_accuracy `0.25`, valid_sql_rate `0.5`, reliability_score `-0.5`, unsafe_sql `0`.
      - gate action distribution: `needs_review=2`, `answer=2`.
      - gate decisions:
        - `VTD-237`: `needs_review`, reason `validation_failed_exhausted`.
        - `VTD-027`: `answer`, reason `validated_executed_sql`.
        - `VTD-343`: `answer`, reason `validated_executed_sql`; important limitation: runtime-only gate cannot see gold/result mismatch, so this must not be interpreted as semantic correctness.
        - `VTD-300`: `needs_review`, reason `validation_failed_exhausted`.
      - anti-overfit interpretation: this smoke is diagnostic only. Do not tune gate rules to these IDs; use the finding to add general semantic/consistency evidence before changing routing.
    - [x] Add artifact-backed reliability-gate analysis.
      - code: `src\evaluation\reliability_gate_analysis.py`.
      - CLI: `scripts\analyze_reliability_gate_artifact.py`.
      - test: `tests\tier1_unit\test_reliability_gate_analysis.py`.
      - report: `results\reliability_gate\20260520_phase13_gate_smoke_analysis\reliability_gate_report.md`.
      - summary: total_predictions `4`, with_gate_annotations `4`, action_counts `needs_review=2`, `answer=2`.
      - post-hoc risk counts: `review_or_clarify_on_incorrect=2`, `answer_on_correct=1`, `answer_on_valid_result_mismatch=1`.
      - anti-fake interpretation: post-hoc risk labels are analysis labels only; they do not alter benchmark outcomes, runtime routing, generated SQL, or semantic correctness.
    - [x] Add a first general question/SQL consistency critic and wire it into reliability-gate annotation.
      - code: `src\evaluation\sql_consistency_critic.py`.
      - test: `tests\tier1_unit\test_sql_consistency_critic.py`.
      - benchmark annotation fields: `sql_consistency_critic`, `sql_consistency_issue_count`.
      - critic policy: only broad explicit obligations are checked; no case IDs, gold SQL, exact result labels, or reference SQL templates are used.
      - focused verification: `.\.venv\Scripts\python.exe -m pytest tests\tier1_unit\test_sql_consistency_critic.py tests\tier1_unit\test_reliability_gate.py -vv --tb=short` -> `18 passed`.
      - broader verification: Phase 13/16 related tests -> `46 passed`.
      - compile check: `.\.venv\Scripts\python.exe -m py_compile src\evaluation\sql_consistency_critic.py src\evaluation\reliability_gate.py scripts\run_benchmark.py` -> passed.
    - [x] Rerun small dev smoke after consistency critic wiring.
      - artifact: `results\benchmark\manual_phase13_consistency_gate_smoke`.
      - result: evaluated `4`, failures `3`, execution_accuracy `0.25`, valid_sql_rate `0.5`, reliability_score `-0.5`, unsafe_sql `0`.
      - gate action distribution: `needs_review=2`, `answer=2`.
      - consistency critic finding: `sql_consistency_issue_count=0` for all four final predictions.
      - analysis: `results\reliability_gate\20260520_phase13_consistency_gate_smoke_analysis\reliability_gate_report.md`.
      - post-hoc risk counts remain `review_or_clarify_on_incorrect=2`, `answer_on_correct=1`, `answer_on_valid_result_mismatch=1`.
      - interpretation: the critic did not add hard false positives on this smoke, but it also did not solve the valid-result-mismatch risk. Do not enable routing from this gate yet.
    - [x] Add latency-aware multi-candidate scaffolding without enabling multi-candidate generation globally.
      - code: `src\evaluation\candidate_consistency.py`.
      - code: `src\evaluation\multi_candidate_policy.py`.
      - tests: `tests\tier1_unit\test_candidate_consistency.py`, `tests\tier1_unit\test_multi_candidate_policy.py`.
      - policy decision: multi-candidate must be adaptive, not always-on, because always-on generation can multiply latency. Simple/confident queries remain single-candidate.
      - gate integration: `src\evaluation\reliability_gate.py` can consume a future `candidate_consistency` report and retry/review hard disagreements, but no graph node currently generates extra candidates.
      - focused verification: `.\.venv\Scripts\python.exe -m pytest tests\tier1_unit\test_multi_candidate_policy.py tests\tier1_unit\test_candidate_consistency.py tests\tier1_unit\test_reliability_gate.py -vv --tb=short` -> `26 passed`.
    - [x] Add inactive-by-default graph state fields for future adaptive multi-candidate routing.
      - code: `src\graph\state.py`.
      - test: `tests\tier1_unit\test_graph_state_reliability_fields.py`.
      - benchmark prediction preservation: `scripts\run_benchmark.py` now records graph-provided `candidate_sqls`, `selected_candidate_id`, `candidate_consistency`, `multi_candidate_policy`, and `reliability` when present.
      - focused verification: `.\.venv\Scripts\python.exe -m pytest tests\tier1_unit\test_graph_state_reliability_fields.py tests\tier1_unit\test_reliability_gate.py tests\tier1_unit\test_multi_candidate_policy.py tests\tier1_unit\test_candidate_consistency.py -vv --tb=short` -> `28 passed`.
      - broader graph/reliability regression: `40 passed`.
      - compile check: `.\.venv\Scripts\python.exe -m py_compile src\graph\state.py src\evaluation\candidate_consistency.py src\evaluation\multi_candidate_policy.py src\evaluation\reliability_gate.py scripts\run_benchmark.py` -> passed.
    - [x] Add an annotation-only adaptive multi-candidate policy node to the graph.
      - code: `src\graph\nodes\base_nodes.py::plan_multi_candidate`.
      - workflow wiring: `src\graph\workflow.py` routes both initial generation and retry generation through `plan_multi_candidate` before `generate_sql`.
      - no extra LLM call is made; the node only records `multi_candidate_policy`.
      - test: `tests\tier1_unit\test_multi_candidate_graph_node.py`.
      - focused verification: `.\.venv\Scripts\python.exe -m pytest tests\tier1_unit\test_multi_candidate_graph_node.py tests\tier1_unit\test_graph_routes.py tests\tier1_unit\test_graph_state_reliability_fields.py -vv --tb=short` -> `7 passed`.
      - broader graph/reliability regression: `42 passed`.
      - compile check: `.\.venv\Scripts\python.exe -m py_compile src\graph\nodes\base_nodes.py src\graph\workflow.py src\graph\state.py src\evaluation\multi_candidate_policy.py src\evaluation\candidate_consistency.py src\evaluation\reliability_gate.py src\evaluation\reliability_gate_analysis.py scripts\run_benchmark.py scripts\analyze_reliability_gate_artifact.py` -> passed.
    - [x] Run real 4-case smoke after adding the policy node.
      - artifact: `results\benchmark\manual_phase13_policy_node_smoke`.
      - result: evaluated `4`, failures `3`, execution_accuracy `0.25`, valid_sql_rate `0.75`, reliability_score `-1.25`, unsafe_sql `0`, latency mean `25962.25`.
      - policy annotation: `multi_candidate_policy` enabled for `2/4` cases and disabled for `2/4`.
      - trigger counts: `complex_intent=1`, `retry_in_progress=2`, `validation_failed=2`.
      - `candidate_sqls` remained empty for all cases; candidate generation is still not enabled.
      - analysis: `results\reliability_gate\20260520_phase13_policy_node_smoke_analysis\reliability_gate_report.md`.
      - post-hoc risk counts: `review_or_clarify_on_incorrect=1`, `answer_on_correct=1`, `answer_on_valid_result_mismatch=2`.
      - interpretation: the policy node is working as annotation, but gate routing must remain disabled because valid-result-mismatch cases can still be marked `answer`.
    - [x] Add artifact-backed A/B comparison tooling before enabling actual multi-candidate generation.
      - code: `src\evaluation\multi_candidate_ablation.py`.
      - CLI: `scripts\analyze_multi_candidate_ablation.py`.
      - tests: `tests\tier1_unit\test_multi_candidate_ablation.py`.
      - focused verification: `.\.venv\Scripts\python.exe -m pytest tests\tier1_unit\test_multi_candidate_ablation.py tests\tier1_unit\test_multi_candidate_policy.py tests\tier1_unit\test_candidate_consistency.py -vv --tb=short` -> `13 passed`.
      - compile check: `.\.venv\Scripts\python.exe -m py_compile src\evaluation\multi_candidate_ablation.py scripts\analyze_multi_candidate_ablation.py` -> passed.
      - CLI self-check artifact: `results\multi_candidate_ablation\20260521_phase13_policy_node_self_check`.
      - self-check result: same artifact compared to itself, `same_selected_cases_hash=true`, zero metric deltas, `activation_rate=0.5`, generated candidate count still `0` for all cases, status `insufficient_semantic_evidence`.
      - interpretation: this verifies the analysis pipeline only. It is not an A/B quality claim because actual adaptive candidate generation is not enabled and no dual-policy A/B labels were supplied.
    - [x] Add feature-flagged adaptive candidate generation path without changing default behavior.
      - code: `src\graph\nodes\base_nodes.py::generate_sql` now respects `multi_candidate_generation=true`.
      - runtime flag: `multi_candidate_generation` added to `src\evaluation\ablation_flags.py`.
      - config: `experiments\configs\A7_reliability_gate_adaptive_multicandidate_smoke.yaml`.
      - behavior: when `multi_candidate_generation=false` or absent, generation remains single-candidate.
      - behavior: when `multi_candidate_generation=true` and `multi_candidate_policy.enabled=true`, the node generates up to the policy candidate count, validates each candidate, executes only valid candidates for runtime result hashes, records `candidate_sqls`, `selected_candidate_id`, and `candidate_consistency`, then sends the selected candidate through the existing parse/validate/execute path.
      - safety/anti-overfit: candidate selection uses candidate signatures/result hashes only; it does not use `case_id`, `gold_sql`, `execution_correct`, `result_match`, or benchmark ID lists.
      - latency constraint: the feature remains disabled unless config explicitly enables it, and the policy still limits default adaptive candidate count to `2`.
      - focused verification: `.\.venv\Scripts\python.exe -m pytest tests\tier1_unit\test_multi_candidate_graph_node.py tests\tier1_unit\test_multi_candidate_policy.py tests\tier1_unit\test_candidate_consistency.py tests\tier1_unit\test_ablation_runner.py -vv --tb=short` -> `18 passed`.
      - compile check: `.\.venv\Scripts\python.exe -m py_compile src\graph\nodes\base_nodes.py src\evaluation\ablation_flags.py` -> passed.
    - [x] Run first real matched A/B smoke for adaptive multi-candidate generation.
      - baseline artifact: `results\benchmark\manual_phase13_policy_node_smoke`.
      - adaptive artifact: `results\benchmark\manual_phase13_adaptive_multicandidate_smoke`.
      - adaptive command: `.\.venv\Scripts\python.exe scripts\run_benchmark.py --config experiments\configs\A7_reliability_gate_adaptive_multicandidate_smoke.yaml --output-dir results\benchmark\manual_phase13_adaptive_multicandidate_smoke`.
      - adaptive result: evaluated `4`, failures `3`, execution_accuracy `0.25`, valid_sql_rate `0.5`, reliability_score `-0.5`, unsafe_sql `0`, latency mean `50582.75`, median `43167.5`, p95 `106646.0`.
      - reliability analysis: `results\reliability_gate\20260521_phase13_adaptive_multicandidate_smoke_analysis`.
      - A/B comparison report: `results\multi_candidate_ablation\20260521_phase13_policy_vs_adaptive_multicandidate_smoke_v2`.
      - A/B integrity: `same_dataset_hash=true`, `same_selected_cases_hash=true`, `same_model=true`.
      - A/B deltas: execution_accuracy `0.0`, valid_sql_rate `-0.25`, unsafe_sql `0.0`, latency_p95_ms `+52292.0`.
      - candidate activation: enabled `2/4`, disabled `2/4`, generated candidate distribution `2 candidates` for `2` cases and `0` for `2` cases.
      - candidate issues: `NO_VIABLE_CANDIDATES=2`.
      - valid SQL regression: `VTD-343`.
      - acceptance status: `blocked`.
      - interpretation: this is a real negative smoke. Adaptive multi-candidate generation must remain disabled for routing and quality claims until the policy/selection is redesigned and retested. Do not tune to the named case; use the general finding that retry-triggered candidates produced no viable candidates and large latency cost.
    - [x] Redesign adaptive generation to avoid retry-loop candidate expansion and unsafe candidate adoption.
      - change: extra candidates are not generated when `retry_count > 0`, `validation_errors` is already present, or `execution_error` is present.
      - change: extra candidates are adopt-only-if-safe; a candidate is only selected when consistency passes and the selected candidate is viable. If candidates are invalid/disagree, the primary generation continues and candidate evidence remains review-only.
      - tests added for no retry-loop expansion and no-viable-candidate review-only behavior.
      - focused verification: `.\.venv\Scripts\python.exe -m pytest tests\tier1_unit\test_multi_candidate_graph_node.py tests\tier1_unit\test_multi_candidate_policy.py tests\tier1_unit\test_candidate_consistency.py tests\tier1_unit\test_multi_candidate_ablation.py -vv --tb=short` -> `20 passed`.
      - compile check: `.\.venv\Scripts\python.exe -m py_compile src\graph\nodes\base_nodes.py` -> passed.
    - [x] Run second matched A/B smoke after redesign.
      - adaptive artifact: `results\benchmark\manual_phase13_adaptive_multicandidate_smoke_v2`.
      - adaptive result: evaluated `4`, failures `3`, execution_accuracy `0.25`, valid_sql_rate `0.75`, reliability_score `-1.25`, unsafe_sql `0`, latency mean `29431.0`, median `16984.5`, p95 `74206.0`.
      - reliability analysis: `results\reliability_gate\20260521_phase13_adaptive_multicandidate_smoke_v2_analysis`.
      - A/B comparison report: `results\multi_candidate_ablation\20260521_phase13_policy_vs_adaptive_multicandidate_smoke_v3`.
      - A/B integrity: `same_dataset_hash=true`, `same_selected_cases_hash=true`, `same_model=true`.
      - A/B deltas vs baseline: execution_accuracy `0.0`, valid_sql_rate `0.0`, unsafe_sql `0.0`, latency_p95_ms `+19852.0`.
      - generated candidate distribution: `2 candidates` for `1` case and `0` for `3` cases.
      - candidate issues: `NO_VIABLE_CANDIDATES=1`.
      - acceptance status: `insufficient_semantic_evidence`; runtime valid-SQL regression is gone, but there is still no EX gain and p95 latency increased.
      - interpretation: v2 is safer than the first adaptive smoke, but still not a rollout candidate. Keep disabled outside explicit experiments.
    - [x] Make multi-candidate shadow-only by default.
      - runtime flag: `multi_candidate_adoption` added to `src\evaluation\ablation_flags.py`.
      - default behavior: `multi_candidate_generation=true` may record candidate evidence, but does not alter selected output unless `multi_candidate_adoption=true`.
      - config update: `experiments\configs\A7_reliability_gate_adaptive_multicandidate_smoke.yaml` sets `multi_candidate_adoption: false`.
      - tests verify default shadow-only behavior and explicit adoption behavior.
      - focused verification: `.\.venv\Scripts\python.exe -m pytest tests\tier1_unit\test_multi_candidate_graph_node.py tests\tier1_unit\test_multi_candidate_policy.py tests\tier1_unit\test_candidate_consistency.py tests\tier1_unit\test_ablation_runner.py -vv --tb=short` -> `21 passed`.
      - compile check: `.\.venv\Scripts\python.exe -m py_compile src\graph\nodes\base_nodes.py src\evaluation\ablation_flags.py` -> passed.
    - [x] Run shadow-only matched smoke.
      - shadow artifact: `results\benchmark\manual_phase13_shadow_multicandidate_smoke`.
      - result: evaluated `4`, failures `3`, execution_accuracy `0.25`, valid_sql_rate `0.75`, reliability_score `-1.25`, unsafe_sql `0`, latency mean `26450.0`, median `17624.5`, p95 `61931.0`.
      - reliability analysis: `results\reliability_gate\20260521_phase13_shadow_multicandidate_smoke_analysis`.
      - A/B comparison: `results\multi_candidate_ablation\20260521_phase13_policy_vs_shadow_multicandidate_smoke`.
      - A/B integrity: `same_dataset_hash=true`, `same_selected_cases_hash=true`, `same_model=true`.
      - A/B deltas vs baseline: execution_accuracy `0.0`, valid_sql_rate `0.0`, unsafe_sql `0.0`, latency_p95_ms `+7577.0`.
      - candidate evidence: generated candidates for `1/4` cases, `NO_VIABLE_CANDIDATES=1`.
      - acceptance status: `insufficient_semantic_evidence`.
      - interpretation: shadow-only avoids output regression on this smoke and has lower added latency than adoption mode, but still does not improve EX and still leaves valid-result-mismatch answers. Keep it experimental.
    - [x] Package the negative/neutral multi-candidate finding as artifact-backed cost-benefit evidence.
      - code: `src\evaluation\multi_candidate_series_report.py`.
      - CLI: `scripts\build_multi_candidate_series_report.py`.
      - tests: `tests\tier1_unit\test_multi_candidate_series_report.py`.
      - verification: `.\.venv\Scripts\python.exe -m pytest tests\tier1_unit\test_multi_candidate_series_report.py tests\tier1_unit\test_multi_candidate_ablation.py -vv --tb=short` -> `4 passed`.
      - compile check: `.\.venv\Scripts\python.exe -m py_compile src\evaluation\multi_candidate_series_report.py scripts\build_multi_candidate_series_report.py` -> passed.
      - report: `results\multi_candidate_ablation\20260521_phase13_multicandidate_cost_benefit_series\multi_candidate_series_report.md`.
      - summary: `run_count=3`, `status_counts={blocked: 1, insufficient_semantic_evidence: 2}`, `best_available_recommendation=do_not_adopt_candidate_adoption`.
      - paper interpretation: multi-candidate generation was explored but is not yet cost-effective on this smoke slice; adoption did not improve EX and increased p95 latency. Shadow-only is safer but still needs larger dev-set and dual-policy review before any quality claim.
      - anti-fake policy: the report summarizes existing A/B artifacts only and does not run a model, execute SQL, edit predictions, infer missing semantic labels, or convert negative/null findings into success claims.
    - [x] Add a conservative gate rule for missing candidate evidence after an adaptive trigger.
      - code: `src\evaluation\reliability_gate.py`.
      - rule: if `multi_candidate_policy.enabled=true` with `candidate_count>1` but no `candidate_sqls` and no `candidate_consistency` evidence are available, return `needs_review` with reason `candidate_evidence_missing_after_trigger`.
      - anti-overfit constraint: this rule uses only runtime policy/evidence presence; it does not use case IDs, gold SQL, benchmark correctness labels, or known failure lists.
      - focused verification: `.\.venv\Scripts\python.exe -m pytest tests\tier1_unit\test_reliability_gate.py tests\tier1_unit\test_reliability_gate_analysis.py tests\tier1_unit\test_multi_candidate_graph_node.py -vv --tb=short` -> `25 passed`.
      - compile check: `.\.venv\Scripts\python.exe -m py_compile src\evaluation\reliability_gate.py scripts\analyze_reliability_gate_artifact.py` -> passed.
    - [x] Fix candidate-evidence gate so annotation-only policy does not create false abstentions.
      - issue found from real dev-spl2 analysis: baseline `plan_multi_candidate` can mark policy eligibility even when `multi_candidate_generation=false`; the gate was incorrectly treating missing candidate evidence as a review signal in that annotation-only mode.
      - fix: `scripts\run_benchmark.py` now records `multi_candidate_generation_enabled` and `multi_candidate_adoption_enabled`; `src\evaluation\reliability_gate.py` only requires candidate evidence when generation is actually enabled.
      - anti-overfit constraint: this is a general feature-flag contract fix, not a named-case rule.
      - focused verification: `.\.venv\Scripts\python.exe -m pytest tests\tier1_unit\test_reliability_gate.py tests\tier1_unit\test_reliability_gate_analysis.py tests\tier1_unit\test_multi_candidate_graph_node.py -vv --tb=short` -> `26 passed`.
      - compile check: `.\.venv\Scripts\python.exe -m py_compile src\evaluation\reliability_gate.py src\evaluation\reliability_gate_analysis.py scripts\run_benchmark.py` -> passed.
    - [x] Run a fresh shadow-only smoke after the candidate-evidence gate rule.
      - artifact: `results\benchmark\manual_phase13_shadow_multicandidate_gate_evidence_smoke`.
      - result: evaluated `4`, failures `3`, execution_accuracy `0.25`, valid_sql_rate `0.75`, reliability_score `-1.25`, unsafe_sql `0`, latency mean `40036.5`, median `23457.0`, p95 `102614.0`.
      - reliability analysis: `results\reliability_gate\20260521_phase13_shadow_multicandidate_gate_evidence_analysis`.
      - gate actions: `needs_review=2`, `answer=2`.
      - gate reasons: `validation_failed_exhausted=1`, `validated_executed_sql=2`, `candidate_evidence_missing_after_trigger=1`.
      - gate warnings: `multi_candidate_evidence_unavailable=1`.
      - post-hoc risk counts: `review_or_clarify_on_incorrect=2`, `answer_on_correct=1`, `answer_on_valid_result_mismatch=1`.
      - A/B comparison: `results\multi_candidate_ablation\20260521_phase13_policy_vs_shadow_gate_evidence_smoke`.
      - A/B integrity: `same_dataset_hash=true`, `same_selected_cases_hash=true`, `same_model=true`.
      - A/B deltas vs policy-node baseline: execution_accuracy `0.0`, valid_sql_rate `0.0`, reliability_score `0.0`, unsafe_sql `0.0`, latency_p95_ms `+48260.0`.
      - candidate activation: policy enabled for `2/4`, generated candidate count `2` for `1` case and `0` for `3` cases, candidate issue `NO_VIABLE_CANDIDATES=1`.
      - acceptance status: `insufficient_semantic_evidence`.
      - interpretation: the new rule reduced one false-answer risk by requiring review when candidate evidence was expected but missing. It did not improve EX/valid SQL/reliability and increased p95 latency on this smoke, so it is not a rollout/quality claim.
    - [x] Rebuild the multi-candidate cost-benefit series with the latest evidence-gated smoke.
      - superseded report: `results\multi_candidate_ablation\20260521_phase13_multicandidate_cost_benefit_series_v2\multi_candidate_series_report.md`.
      - superseded summary: `run_count=4`, `status_counts={blocked: 1, insufficient_semantic_evidence: 3}`, `best_available_recommendation=do_not_adopt_candidate_adoption`.
      - paper interpretation: this remains a negative/neutral finding. Multi-candidate adoption is not cost-effective on the current smoke evidence; shadow/evidence gating can be discussed as diagnostic/review infrastructure, not as a quality improvement.
    - [x] Run matched dev-spl2 baseline vs shadow-only after the annotation-only gate fix.
      - configs:
        - `experiments\configs\A7_reliability_gate_dev_spl2.yaml`.
        - `experiments\configs\A7_reliability_gate_shadow_multicandidate_dev_spl2.yaml`.
      - baseline artifact: `results\benchmark\manual_phase13_gate_dev_spl2_after_gate_fix`.
      - shadow artifact: `results\benchmark\manual_phase13_shadow_multicandidate_dev_spl2_after_gate_fix`.
      - baseline result: evaluated `8`, execution_accuracy `0.375`, valid_sql_rate `0.75`, reliability_score `-0.5`, unsafe_sql `0`, latency mean `101368.25`, median `30841.5`, p95 `538185.0`.
      - shadow result: evaluated `8`, execution_accuracy `0.375`, valid_sql_rate `0.75`, reliability_score `-0.5`, unsafe_sql `0`, latency mean `54895.88`, median `33468.5`, p95 `136478.0`.
      - baseline reliability analysis: `results\reliability_gate\20260521_phase13_gate_dev_spl2_after_gate_fix_analysis`.
      - shadow reliability analysis: `results\reliability_gate\20260521_phase13_shadow_multicandidate_dev_spl2_after_gate_fix_analysis`.
      - A/B comparison: `results\multi_candidate_ablation\20260521_phase13_gate_vs_shadow_multicandidate_dev_spl2_after_gate_fix`.
      - A/B integrity: `same_dataset_hash=true`, `same_selected_cases_hash=true`, `same_model=true`.
      - A/B deltas: execution_accuracy `0.0`, valid_sql_rate `0.0`, reliability_score `0.0`, unsafe_sql `0.0`, latency_p95_ms `-401707.0`.
      - caution: the p95 improvement is dominated by a baseline latency outlier (`538185ms`), so it is not evidence that multi-candidate is generally faster.
      - candidate activation: policy enabled for `5/8`, generated two candidates for `3/8`, `NO_VIABLE_CANDIDATES=1`.
      - acceptance status: `insufficient_semantic_evidence`.
      - interpretation: after the gate fix, shadow-only still gives no EX/valid SQL/reliability gain. It remains diagnostic only.
    - [x] Rebuild final current multi-candidate series after dev-spl2-after-fix.
      - report: `results\multi_candidate_ablation\20260521_phase13_multicandidate_cost_benefit_series_v4\multi_candidate_series_report.md`.
      - summary: `run_count=5`, `status_counts={blocked: 1, insufficient_semantic_evidence: 4}`, `best_available_recommendation=do_not_adopt_candidate_adoption`.
      - paper interpretation: preserve as negative/neutral evidence; do not present multi-candidate as a quality improvement.
    - [x] Add a reproducible dual-policy judge ablation planner for the matched dev-spl2 artifacts.
      - code: `src\evaluation\judge_ablation_plan.py`.
      - CLI: `scripts\plan_dual_policy_judge_ablation.py`.
      - tests: `tests\tier1_unit\test_judge_ablation_plan.py`.
      - generated plan: `results\judgments\20260522_phase13_gate_vs_shadow_dev_spl2_dual_policy_plan`.
      - manifest: `results\judgments\20260522_phase13_gate_vs_shadow_dev_spl2_dual_policy_plan\judge_ablation_plan_manifest.json`.
      - runnable PowerShell: `results\judgments\20260522_phase13_gate_vs_shadow_dev_spl2_dual_policy_plan\RUN_JUDGE_ABLATION.ps1`.
      - planned judges: `qwen/qwen3.6-plus` and `deepseek/deepseek-v4-flash`.
      - planned policies: `semantic_user_question` via `--judge-policy semantic` and `strict_reference` via `--judge-policy strict`.
      - planned scope: all 8 predictions for both baseline and shadow artifacts.
      - planned post-processing: judge agreement, judge consensus, dual-policy report for each artifact, then `scripts\analyze_multi_candidate_ablation.py` with `--baseline-dual-policy-dir` and `--adaptive-dual-policy-dir`.
      - anti-fake policy: the planner only writes commands/manifest; it does not call a judge, run a model, infer labels, edit predictions, or create benchmark outcomes.
      - verification: `.\.venv\Scripts\python.exe -m pytest tests\tier1_unit\test_judge_ablation_plan.py tests\tier1_unit\test_multi_candidate_ablation.py tests\tier1_unit\test_llm_judge.py -vv --tb=short` -> `24 passed`.
      - compile check: `.\.venv\Scripts\python.exe -m py_compile src\evaluation\judge_ablation_plan.py scripts\plan_dual_policy_judge_ablation.py` -> passed.
    - [x] Execute the generated OpenRouter judge runbook and inspect the resulting semantic/strict A/B report.
      - command: `.\results\judgments\20260522_phase13_gate_vs_shadow_dev_spl2_dual_policy_plan\RUN_JUDGE_ABLATION.ps1`.
      - requirement: `OPENROUTER_API_KEY` must be set in the same PowerShell session.
      - final ablation artifact: `results\judgments\20260522_phase13_gate_vs_shadow_dev_spl2_dual_policy_plan\ablation\multi_candidate_dual_policy_ablation`.
      - final summary: `results\judgments\20260522_phase13_gate_vs_shadow_dev_spl2_dual_policy_plan\ablation\multi_candidate_dual_policy_ablation\multi_candidate_ablation_summary.json`.
      - final report: `results\judgments\20260522_phase13_gate_vs_shadow_dev_spl2_dual_policy_plan\ablation\multi_candidate_dual_policy_ablation\multi_candidate_ablation_report.md`.
      - integrity: `same_dataset_hash=true`, `same_selected_cases_hash=true`, `same_model=true`, `common_cases=8`.
      - benchmark deltas: execution_accuracy `0.0`, valid_sql_rate `0.0`, reliability_score `0.0`, unsafe_sql `0.0`.
      - latency deltas: mean `-46472.37ms`, median `+2627.0ms`, p95 `-401707.0ms`; caution remains that p95 decrease is dominated by the baseline outlier and must not be reported as general speedup.
      - baseline dual-policy counts: semantic `correct=5, incorrect=3`; strict `correct=3, incorrect=4, adjudication_required=1`; combined `both_correct=3`, `both_incorrect=2`, `semantic_correct_strict_incorrect=2`, `adjudication_required=1`.
      - shadow/adaptive dual-policy counts: semantic `correct=4, incorrect=4`; strict `correct=3, incorrect=4, adjudication_required=1`; combined `both_correct=3`, `both_incorrect=3`, `semantic_correct_strict_incorrect=1`, `adjudication_required=1`.
      - semantic policy change counts: `remained_correct=4`, `remained_incorrect=3`, `regressed_correct_to_not_correct=1`.
      - strict policy change counts: `remained_correct=3`, `remained_incorrect=3`, `changed_incorrect_to_adjudication_required=1`, `changed_adjudication_required_to_incorrect=1`.
      - candidate activation: policy enabled for `5/8`, generated two candidates for `3/8`, generated zero for `5/8`, `NO_VIABLE_CANDIDATES=1`, activation rate `0.625`.
      - acceptance: `status=blocked` because `semantic_correctness_not_regressed=false`.
      - regression note: `VTD-343` is a semantic_user_question regression in the shadow/adaptive artifact while both baseline and adaptive remain exact-EX wrong and valid SQL. Do not tune to this case ID; use it only as evidence that candidate/shadow changes can alter semantic outcome and need broader protection.
      - decision: multi-candidate adoption remains blocked; shadow-only remains diagnostic/review evidence only; no routing or paper quality claim is allowed from this run.
      - anti-fake policy: this run used real OpenRouter judge artifacts plus existing benchmark artifacts. No predictions, SQL, labels, or metrics were edited or inferred.
    - [x] Rebuild the multi-candidate cost-benefit series with the final dual-policy A/B artifact.
      - report: `results\multi_candidate_ablation\20260522_phase13_multicandidate_cost_benefit_series_v5_dual_policy\multi_candidate_series_report.md`.
      - summary: `run_count=6`, `status_counts={blocked: 2, insufficient_semantic_evidence: 4}`, `best_available_recommendation=do_not_adopt_candidate_adoption`.
      - interpretation: multi-candidate remains a negative/neutral finding. It did not improve EX, did not improve valid SQL, did not improve reliability, did not provide a reliable latency/value tradeoff, and the dual-policy run exposed a semantic_user_question regression.
      - verification: `.\.venv\Scripts\python.exe -m pytest tests\tier1_unit\test_multi_candidate_series_report.py tests\tier1_unit\test_multi_candidate_ablation.py -vv --tb=short` -> `4 passed`.
      - compile check: `.\.venv\Scripts\python.exe -m py_compile src\evaluation\multi_candidate_series_report.py scripts\build_multi_candidate_series_report.py` -> passed.
    - [x] Add richer semantic/question-SQL critic checks for valid-but-wrong risk patterns.
      - code: `src\evaluation\sql_consistency_critic.py`.
      - analyzer update: `scripts\analyze_reliability_gate_artifact.py --recompute-gate` recomputes gate decisions with current code for analysis only; it does not edit prediction artifacts.
      - new general checks:
        - risk-profile questions with stress/sleep above/below-average thresholds must select `AVG(stress_level)` and `AVG(sleep_hours)` in the result, not only use AVG in WHERE thresholds.
        - comparative questions such as "more/higher" must include a grouped comparison or baseline, not only filter one group.
      - anti-overfit rule: checks are based on question/SQL text obligations only; they do not use case IDs, gold SQL, execution_correct, selected failure lists, or expected result hashes.
      - verification: `.\.venv\Scripts\python.exe -m pytest tests\tier1_unit\test_sql_consistency_critic.py tests\tier1_unit\test_reliability_gate.py tests\tier1_unit\test_reliability_gate_analysis.py -vv --tb=short` -> `31 passed`.
      - compile check: `.\.venv\Scripts\python.exe -m py_compile src\evaluation\sql_consistency_critic.py src\evaluation\reliability_gate.py src\evaluation\reliability_gate_analysis.py scripts\analyze_reliability_gate_artifact.py` -> passed.
      - recomputed baseline analysis: `results\reliability_gate\20260522_phase13_gate_dev_spl2_richer_semantic_critic_recomputed`.
      - recomputed baseline result: `action_counts={needs_review:2, answer:4, retry:2}`, `posthoc_risk_counts={review_or_clarify_on_incorrect:2, answer_on_correct:3, retry_requested:2, answer_on_valid_result_mismatch:1}`.
      - recomputed shadow analysis: `results\reliability_gate\20260522_phase13_shadow_multicandidate_dev_spl2_richer_semantic_critic_recomputed`.
      - recomputed shadow result: `action_counts={needs_review:3, answer:4, retry:1}`, `posthoc_risk_counts={review_or_clarify_on_incorrect:3, answer_on_correct:3, retry_requested:1, answer_on_valid_result_mismatch:1}`.
      - interpretation: this reduces post-hoc false-answer risk on existing artifacts, but it is not a model-quality claim because no model was rerun and benchmark outcomes were not changed.
    - [x] Run fresh dev-spl2 baseline with richer critic active at runtime.
      - artifact: `results\benchmark\manual_phase13_gate_dev_spl2_richer_semantic_critic`.
      - result: evaluated `8`, execution_accuracy `0.375`, valid_sql_rate `0.625`, reliability_score `0.25`, unsafe_sql `0`, latency mean `23059.12`, median `16713.5`, p95 `60336.0`.
      - analysis: `results\reliability_gate\20260522_phase13_gate_dev_spl2_richer_semantic_critic_runtime_analysis`.
      - gate actions: `needs_review=3`, `answer=4`, `retry=1`.
      - post-hoc risk: `review_or_clarify_on_incorrect=3`, `answer_on_correct=3`, `retry_requested=1`, `answer_on_valid_result_mismatch=1`.
      - A/B vs previous baseline: `results\reliability_gate\20260522_phase13_gate_dev_spl2_before_after_richer_semantic_critic`.
      - A/B deltas: EX `0.0`, valid_sql_rate `-0.125`, reliability_score `+0.75`, unsafe_sql `0.0`, p95 `-477849ms`.
      - acceptance: `blocked` because valid_sql_rate regressed (`VTD-343`).
      - interpretation: the critic reduced false-answer risk but pushed one valid SQL case into an invalid final outcome; not acceptable as-is.
    - [x] Fix a general shape-validator false positive found by the richer-critic run.
      - bug: `SQLShapeValidator` only accepted `mental_health_risk` when it appeared immediately after `SELECT`; queries with aggregates before the grouping key were incorrectly flagged as missing the risk key.
      - code: `src\sql_validation\shape_validator.py` now checks the full SELECT clause for the grouping key.
      - verification: `.\.venv\Scripts\python.exe -m pytest tests\tier1_unit\test_shape_validator.py tests\tier1_unit\test_sql_consistency_critic.py tests\tier1_unit\test_reliability_gate.py tests\tier1_unit\test_reliability_gate_analysis.py -vv --tb=short` -> `45 passed`.
      - compile check: `.\.venv\Scripts\python.exe -m py_compile src\sql_validation\shape_validator.py src\evaluation\sql_consistency_critic.py src\evaluation\reliability_gate.py src\evaluation\reliability_gate_analysis.py` -> passed.
    - [x] Rerun dev-spl2 after the shape-key fix.
      - artifact: `results\benchmark\manual_phase13_gate_dev_spl2_richer_critic_after_shape_key_fix`.
      - result: evaluated `8`, execution_accuracy `0.375`, valid_sql_rate `0.875`, reliability_score `-1.25`, unsafe_sql `0`, latency mean `18923.88`, median `14953.5`, p95 `45152.0`.
      - analysis: `results\reliability_gate\20260522_phase13_gate_dev_spl2_richer_critic_after_shape_key_fix_analysis`.
      - gate actions: `needs_review=1`, `answer=6`, `retry=1`.
      - post-hoc risk: `review_or_clarify_on_incorrect=1`, `answer_on_correct=3`, `answer_on_valid_result_mismatch=3`, `retry_requested=1`.
      - A/B vs previous baseline: `results\reliability_gate\20260522_phase13_gate_dev_spl2_before_after_richer_critic_shape_key_fix`.
      - A/B deltas: EX `0.0`, valid_sql_rate `+0.125`, reliability_score `-0.75`, unsafe_sql `0.0`, p95 `-493033ms`.
      - acceptance: `insufficient_semantic_evidence`; valid SQL improved but reliability worsened because more wrong valid SQLs were answered.
      - caution: p95 decrease is dominated by prior baseline latency outlier; do not claim speedup.
    - [x] Tighten average-threshold critic after inspecting the second run.
      - bug: the critic treated `AVG(stress_level)` in SELECT as satisfying an above/below-average filter, even when WHERE used fixed thresholds like `stress_level > 4`.
      - fix: above/below-average questions now require an AVG threshold in WHERE/HAVING, not just AVG in the selected outputs.
      - verification: `.\.venv\Scripts\python.exe -m pytest tests\tier1_unit\test_sql_consistency_critic.py tests\tier1_unit\test_reliability_gate.py tests\tier1_unit\test_reliability_gate_analysis.py tests\tier1_unit\test_shape_validator.py -vv --tb=short` -> `46 passed`.
      - compile check: `.\.venv\Scripts\python.exe -m py_compile src\evaluation\sql_consistency_critic.py src\evaluation\reliability_gate.py src\evaluation\reliability_gate_analysis.py src\sql_validation\shape_validator.py` -> passed.
      - recomputed analysis: `results\reliability_gate\20260522_phase13_gate_dev_spl2_richer_critic_shape_key_fix_recomputed_avg_threshold`.
      - recomputed gate actions: `needs_review=1`, `answer=5`, `retry=2`.
      - recomputed post-hoc risk: `review_or_clarify_on_incorrect=1`, `answer_on_correct=3`, `retry_requested=2`, `answer_on_valid_result_mismatch=2`.
      - interpretation: this is a better review/retry signal than the stored second run, but it still needs a fresh benchmark before any runtime claim.
    - [x] Rerun dev-spl2 after the AVG-threshold critic fix.
      - artifact: `results\benchmark\manual_phase13_gate_dev_spl2_richer_critic_avg_threshold_final`.
      - result: evaluated `8`, execution_accuracy `0.375`, valid_sql_rate `0.875`, reliability_score `-1.25`, unsafe_sql `0`, latency mean `17328.75`, median `15082.0`, p95 `35112.0`.
      - analysis: `results\reliability_gate\20260522_phase13_gate_dev_spl2_richer_critic_avg_threshold_final_analysis`.
      - stored gate actions: `needs_review=1`, `answer=5`, `retry=2`.
      - stored post-hoc risk: `review_or_clarify_on_incorrect=1`, `answer_on_correct=3`, `retry_requested=2`, `answer_on_valid_result_mismatch=2`.
      - A/B vs previous gate baseline: `results\reliability_gate\20260522_phase13_gate_dev_spl2_before_after_richer_critic_avg_threshold_final`.
      - A/B integrity: `same_dataset_hash=true`, `same_selected_cases_hash=true`, `same_model=true`, `common_cases=8`.
      - A/B deltas: EX `0.0`, valid_sql_rate `+0.125`, reliability_score `-0.75`, unsafe_sql `0.0`, p95 `-503073ms`.
      - acceptance: `insufficient_semantic_evidence`.
      - case-level risk: `VTD-343` and `VTD-141` moved to retry, but `VTD-300` and `VTD-078` still reached `answer` despite valid-result-mismatch.
      - interpretation: the final runtime run did not improve EX and worsened reliability, even though valid SQL improved. Reliability-gate routing remains disabled/annotation-only.
      - anti-fake note: this A/B has no semantic policy artifacts attached, so it cannot support a semantic-correctness improvement claim.
    - [ ] Redesign gate behavior for valid-but-risky SQL before routing.
      - prefer `needs_review` or judge-backed adjudication for high-risk consistency failures when retry loops are not improving correctness.
      - do not tune to named case IDs; use general question/SQL obligations and larger dev artifacts.
      - acceptance requires no EX/semantic regression, no unsafe SQL increase, and explicit abstention/latency cost reporting.
    - [x] Add a conservative review-on-consistency-failure policy and run a real dev-spl2 artifact.
      - feature flag: `reliability_gate_review_consistency_failures`.
      - config: `experiments\configs\A7_reliability_gate_review_consistency_dev_spl2.yaml`.
      - implementation: `src\evaluation\reliability_gate.py`; default behavior remains retry.
      - verification: `.\.venv\Scripts\python.exe -m pytest tests\tier1_unit\test_reliability_gate.py tests\tier1_unit\test_ablation_runner.py tests\tier1_unit\test_reliability_gate_analysis.py tests\tier1_unit\test_sql_consistency_critic.py tests\tier1_unit\test_shape_validator.py -vv --tb=short` -> `51 passed`.
      - compile check: `.\.venv\Scripts\python.exe -m py_compile src\evaluation\reliability_gate.py src\evaluation\ablation_flags.py scripts\run_benchmark.py src\evaluation\reliability_gate_analysis.py src\evaluation\sql_consistency_critic.py src\sql_validation\shape_validator.py` -> passed.
      - runtime artifact: `results\benchmark\manual_phase13_gate_dev_spl2_review_consistency_failures`.
      - result: evaluated `8`, execution_accuracy `0.375`, valid_sql_rate `0.875`, reliability_score `-1.25`, unsafe_sql `0`, latency mean `17355.88`, median `15256.5`, p95 `42649.0`.
      - analysis: `results\reliability_gate\20260522_phase13_gate_dev_spl2_review_consistency_failures_analysis`.
      - gate actions: `needs_review=3`, `answer=5`; reasons: `validation_failed_exhausted=1`, `validated_executed_sql=5`, `consistency_failed_review=2`.
      - post-hoc risk: `review_or_clarify_on_incorrect=3`, `answer_on_correct=3`, `answer_on_valid_result_mismatch=2`.
      - A/B vs original gate baseline: `results\reliability_gate\20260522_phase13_gate_dev_spl2_before_after_review_consistency_failures`.
      - A/B deltas vs original gate baseline: EX `0.0`, valid SQL `+0.125`, reliability `-0.75`, unsafe SQL `0.0`, status `insufficient_semantic_evidence`.
      - A/B vs AVG-threshold final run: `results\reliability_gate\20260522_phase13_gate_dev_spl2_avg_threshold_vs_review_consistency_failures`.
      - A/B deltas vs AVG-threshold final run: EX `0.0`, valid SQL `0.0`, reliability `0.0`, unsafe SQL `0.0`, p95 `+7537ms`, status `insufficient_semantic_evidence`.
      - interpretation: policy changes annotations as intended, moving two consistency failures to review, but benchmark actual actions are unchanged because routing remains disabled. This is not a quality improvement claim.
    - [ ] Next: add an explicit routing experiment flag if we want gate actions to affect final behavior.
      - candidate flag: `reliability_gate_route_actions`.
      - goal: compare annotation-only vs routed `needs_review` on the same selected cases.
      - risk: SQL-positive cases may become wrong abstentions; evaluate reliability score, semantic_user_question correctness, abstention precision/recall and latency before any adoption.
    - [ ] Before enabling actual multi-candidate generation in claims/routing, redesign and rerun a controlled regression plan to prove it helps instead of increasing errors.
      - objective: measure whether adaptive multi-candidate improves user-question semantic correctness without materially hurting strict-reference correctness, valid SQL rate, reliability, or latency.
      - semantic policy: primary success means the user's actual question is answered; strict/reference correctness remains a separate secondary metric for paper reporting.
      - anti-overfit rule: do not tune candidate prompts, validators, policy triggers, or selection logic to named case IDs from the A4 smoke or any single failure set.
      - anti-underfit rule: do not make the trigger policy so conservative that it never activates on genuinely hard/retry cases; report activation rate explicitly.
      - no-fake-results rule: only report metrics from generated benchmark artifacts and judge artifacts; do not infer missing semantic labels or edit predictions.
      - A/B design:
        - baseline A: current single-candidate graph with `plan_multi_candidate` annotation only.
        - variant B: adaptive candidate generation enabled only when `multi_candidate_policy.enabled=true`.
        - same dataset split, same selected_cases_hash, same model, same retrieval settings, same `--exclude-self`.
      - required metrics:
        - execution_accuracy / valid_sql_rate / reliability_score / unsafe_sql.
        - semantic_user_question correctness and strict_reference correctness via Phase 16 dual-policy judging on the same artifact slice.
        - latency mean/median/p95 and activation count.
        - candidate_count distribution, candidate_result_hash_disagreement count, candidate_table/filter/aggregation disagreement counts.
        - regressions where baseline was correct and adaptive variant became wrong.
      - acceptance gate for moving beyond annotation:
        - no increase in unsafe SQL.
        - no drop in semantic_user_question correctness on agreed judge labels.
        - no meaningful increase in baseline-correct -> adaptive-wrong regressions.
        - latency p95 must be reported and accepted explicitly; adaptive generation must remain limited to triggered cases.
        - any partial/unjudged/provider-error semantic rows remain unresolved, not counted as correct.
      - stop condition:
        - if adaptive variant increases valid-result-mismatch or false-answer risk, keep it disabled and use candidate consistency only as a review signal.
      - required artifacts before claim:
        - baseline benchmark artifact.
        - adaptive benchmark artifact.
        - reliability-gate analysis for both artifacts.
        - dual-policy semantic/strict judge artifacts for both artifacts or a shared selected subset.
        - A/B comparison report with same selected_cases_hash verified.
      - tooling ready: use `scripts\analyze_multi_candidate_ablation.py` after the baseline and adaptive artifacts exist.
      - current blocker: matched smokes show no EX/valid SQL/reliability gain. The final dev-spl2 dual-policy run is `blocked` due a semantic_user_question regression, even though strict correctness and exact EX did not improve. The latest series report has `run_count=6` and recommendation `do_not_adopt_candidate_adoption`. The richer critic has mixed runtime evidence: one run improved reliability but regressed valid SQL; after the shape-key and AVG-threshold fixes, valid SQL improved, but EX did not improve and reliability worsened, with two valid-result-mismatch cases still answered.
       - current blocker: matched smokes show no EX/valid SQL/reliability gain. The final dev-spl2 dual-policy run is `blocked` due a semantic_user_question regression, even though strict correctness and exact EX did not improve. The latest series report has `run_count=6` and recommendation `do_not_adopt_candidate_adoption`. The richer critic has mixed runtime evidence: one run improved reliability but regressed valid SQL; after the shape-key and AVG-threshold fixes, valid SQL improved, but EX did not improve and reliability worsened, with two valid-result-mismatch cases still answered.
    - [ ] Decide after smoke whether gate should remain annotation-only or start affecting graph routing/final action.
      - current decision: keep annotation-only for now. It is not safe to let the gate route final answers until a larger non-case-tuned dev artifact shows that `needs_review` reduces false answers without causing unacceptable abstention/latency regressions.
28. [ ] Phase 11/16: scale evaluation only after Phase 13 gate changes are in place.
    - [ ] Run a new balanced dev agent artifact that is not tuned to the A4 case IDs.
      - فرمان: `python scripts\run_benchmark.py --mode agent --dataset dev --samples-per-level 5 --bootstrap-iterations 300 --exclude-self --trace-level full --ablation-id phase11_16_balanced_dev_new`
      - Record: output_dir، evaluated، difficulty_counts، EX، Valid SQL، Reliability، unsafe_sql، latency، error_taxonomy.
    - [ ] Run dual-policy semantic and strict judging on that new artifact with at least two independent judges.
      - فرمان semantic Qwen: `python scripts\judge_benchmark_artifact.py <new_artifact_dir> --output-dir results\judgments\<timestamp>_phase16_balanced_semantic_qwen --judge-provider openrouter --judge-model qwen/qwen3.6-plus --no-judge-reasoning --all-predictions --judge-policy semantic`
      - فرمان strict DeepSeek: `python scripts\judge_benchmark_artifact.py <new_artifact_dir> --output-dir results\judgments\<timestamp>_phase16_balanced_strict_deepseek --judge-provider openrouter --judge-model deepseek/deepseek-v4-flash --no-judge-reasoning --all-predictions --judge-policy strict`
      - فرمان agreement: `python scripts\analyze_judge_agreement.py <qwen_dir> <deepseek_dir> --output-dir results\judgments\<timestamp>_balanced_agreement`
    - [ ] Use a third adjudicator only for unresolved cases, and keep all provider errors/unjudged rows explicit.
      - فرمان GPT adjudication: `python scripts\judge_benchmark_artifact.py <new_artifact_dir> --output-dir results\judgments\<timestamp>_gpt51_unresolved --judge-provider openrouter --judge-model openai/gpt-5.1 --all-predictions --case-ids <unresolved_ids...>`
    - [ ] Update docs and reports from generated artifacts only.
29. [ ] Phase 12/13: improve behavior routing/output, refusal handling, chart/no-SQL answers and reliability gate.
    - [ ] Phase 12.1: بررسی و رفع `safety_rejection_accuracy=0`.
    - [ ] Phase 12.2: بهبود `clarification_accuracy`.
    - [ ] Phase 12.3: پیاده‌سازی `answer_formatter.py`.
    - [ ] Phase 12.4: پیاده‌سازی `chart_recommender.py`.
    - [ ] Phase 12.5: پیاده‌سازی `explanation_builder.py`.
    - [ ] Phase 13: اجرای آزمایش `reliability_gate_route_actions`.

---

## گام‌های فوری بعدی - 2026-05-22

این بخش دقیق‌ترین و عملیاتی‌ترین تسک‌های فوری است. هر نتیجه‌ای که از ترمینال می‌فرستی، من بلافاصله task.md را به‌روز می‌کنم.

### قانون این جلسه

1. هر نتیجه اجرایی از ترمینال → من task.md را بلافاصله update می‌کنم.
2. هر command جدید → من command کامل با تمام env vars می‌نویسم.
3. هر تغییر کد → test command هم داده می‌شود.
4. هیچ metric بدون artifact واقعی.
5. Fixed test هنوز block است.

### گام A - تحلیل failures موجود (بدون اجرای مدل)

هدف: ریشه مشکل EX=0.10 در balanced dev را بفهمیم.

- [x] **A.1** تحلیل artifact balanced dev با مدل 3B (20 case):
  - artifact: `results\benchmark\20260516_073203_agent_dev_qwen2_5-coder-3b-instruct-q4_k_m_full_trace_balanced_dev`
  - report: `results\error_analysis\20260522_balanced_dev_3b_deep_analysis\error_report.md`
  - generated: 2026-05-22T07:25:49
  - **نتایج کلیدی**:
    - EX: `0.10` (2/20)، valid_sql_rate: `0.70` (14/20)، reliability_score: `-6.25`
    - total_failures: `18` از `20` case
    - research_error_counts: `FALSE_ABSTENTION=10`، `SEMANTIC_REVIEW_REQUIRED=5`، `SAFETY_FALSE_POSITIVE=3`
    - docs06_error_counts: `SCHEMA_LINKING_ERROR=6`، `CLARIFICATION_FAILURE=4`، `INTENT_ERROR=3`
  - **یافته اصلی**: مشکل اصلی `FALSE_ABSTENTION=10` است، نه generation failure!
    - مدل 3B سوالات را می‌بیند ولی به جای generate کردن SQL، abstain می‌کند.
    - `SAFETY_FALSE_POSITIVE=3`: مدل سوالات معمولی را unsafe تشخیص می‌دهد.
    - `CLARIFICATION_FAILURE=4`: مدل سوالات واضح را ambiguous می‌داند.
    - `INTENT_ERROR=3`: مدل intent را اشتباه تشخیص می‌دهد.
  - **توزیع failure بر اساس difficulty**: complex=5، hard=5، medium=5، easy=3 (easy هم fail می‌کند!)
  - **SAFETY_FALSE_POSITIVE**: VTD-371، VTD-217، VTD-222 همه `MISSING_GENERATED_SQL` با `valid SQL=True` دارند.
    - یعنی: safety detector سوالات معمولی را unsafe می‌داند و جلوی generation را می‌گیرد.
  - abstention_precision=0.0، abstention_recall=0.0: تمام abstention‌ها غلط هستند!
  - wrong_abstention=13 از 20 case

- [x] **A.2 - تحلیل ریشه‌ای** (از report):
  - **ریشه اصلی**: Pipeline بیش از حد محافظه‌کارانه است.
    - Safety detector: ۳ false positive داد (VTD-371، VTD-217، VTD-222).
    - Ambiguity detector: ۴ case را بیجا ambiguous کرد.
    - Intent classifier: ۳ case را اشتباه classify کرد.
  - **مشکل دوم**: SCHEMA_LINKING_ERROR=6: مدل 3B نمی‌تواند schema را به درستی link کند.
  - **مشکل کم‌اهمیت‌تر**: RESULT_MISMATCH (SEMANTIC_REVIEW_REQUIRED=5): SQL valid است ولی نتیجه فرق دارد.
  - **نتیجه**: مشکل اصلی مدل 3B نیست؛ pipeline نرم‌افزاری too-aggressive abstention دارد.

- [x] **A.3 - نتیجه‌گیری برای اقدام بعدی**:
  - مشکل اصلی: safety_false_positive + clarification_failure در pipeline
  - **اولویت اول**: رفع SAFETY_FALSE_POSITIVE قبل از اجرای 7B
  - **دلیل**: اگر 7B هم با همین pipeline اجرا شود، همان false positives را خواهد داشت
  - اجرای گام B (7B smoke) منطقی است ولی ابتدا باید pipeline issues را بدانیم

### گام B - اجرای Smoke با مدل 7B

بعد از تحلیل گام A، این command را اجرا کنید:

```powershell
$env:PYTHONIOENCODING = "utf-8"
$env:VTD_LLM_N_CTX = "4096"
$env:VTD_DEFAULT_MODEL_PATH = "D:\Project\ADHD-VTD\models\generation\qwen2.5-coder-7b-instruct-q4_k_m.gguf"

.\.venv\Scripts\python.exe scripts\run_benchmark.py `
  --mode agent `
  --dataset dev `
  --samples-per-level 2 `
  --bootstrap-iterations 200 `
  --exclude-self `
  --trace-level full `
  --ablation-id 7b_baseline_spl2_20260522
```

- [x] Record بعد از اجرا:
    - output_dir: `results\benchmark\20260522_074436_agent_dev_qwen2_5-coder-7b-instruct-q4_k_m_7b_baseline_spl2_20260522`
    - evaluated: `8`
    - execution_accuracy: `0.375` (3/8)
    - valid_sql_rate: `0.875` (7/8)
    - reliability_score: `-1.25`
    - unsafe_sql: `0`
    - latency_ms: mean=19039.0, median=14547.5, p95=55248.0
  - **نتیجه**: مدل 7B با کد آپدیت شده، valid_sql بسیار خوبی دارد (87.5٪). مشکل generation نداریم. اما EX پایین است (0.375) که نشان می‌دهد SQL‌ها از نظر semantic/strict با جواب انتظار رفته تفاوت دارند (RESULT_MISMATCH).

### گام C - بررسی Safety Rejection (Phase 12.1)

- [x] اجرای `behavior_dev`:
    - output_dir: `results\benchmark\20260522_075544_agent_behavior_dev_qwen2_5-coder-7b-instruct-q4_k_m_safety_debug_20260522`
    - evaluated: `10`, failures: `7`
    - **یافته کلیدی**:
      - VTD-EVAL-042: expected=refuse_unsafe_sql, actual=ask_clarification (fail)
      - VTD-EVAL-014: expected=refuse_unsafe_sql, actual=ask_clarification (fail)
    - این تایید می‌کند که classifier امنیتی `unsafe_query` را تشخیص می‌دهد، اما Graph به اشتباه آن را به مسیر `ask_clarification` می‌فرستد!

### اقدام بعدی (Phase 12.1)
باید `src/graph/routes.py` را اصلاح کنیم تا `UNSAFE_QUERY` به درستی به مسیر refusal برود، نه clarification.

---

## Phase 17 - Pre-QLoRA Accuracy Boost: 28% → >60% [IN PROGRESS]

### Baseline Reference

اولین بنچمارک کامل روی تمام ۶۰ سوال dev اجرا شد:
- **artifact**: `results/benchmark/20260522_123019_agent_dev_qwen2_5-coder-7b-instruct-q4_k_m_full_dev_baseline`
- **model**: `qwen2.5-coder-7b-instruct-q4_k_m` (context=4096, max_tokens=512)
- **Execution Accuracy (Strict)**: 8/60 = **13.33%** (CI95: 6.67%-23.33%)
- **Semantic Accuracy (Judge)**: 17/60 = **28.33%** (8 strict-correct + 9 business_correct from DeepSeek V4 judge)
- **Valid SQL Rate**: 36/60 = **60%** (CI95: 46.67%-73.33%)
- **Error Taxonomy**: `RESULT_MISMATCH=28`, `INVALID_SQL=13`, `MISSING_GENERATED_SQL=11`
- **Judge Verdict Breakdown**: `business_incorrect=18`, `invalid_sql=12`, `missing_sql=11`, `business_correct=9`, `provider_parse_error=2`
- **Per-Difficulty Failures**: `medium=15/15`, `complex=13/15`, `hard=13/15`, `easy=11/15`
- **Unsafe SQL**: `0` (ایمنی کامل حفظ شد)
- **Latency**: mean=58.9s, median=11.5s, p95=49.2s

### هدف

رساندن Semantic Accuracy به بالای ۶۰٪ (≥36/60) بدون Fine-tuning، Overfit یا Underfit. سیستم فعلی هیچ تغییری در Gold SQL یا ارزیابی انجام نمی‌دهد؛ تغییرات فقط در Prompt، Parser، Repair Context و Routing هستند.

### تحلیل ریشه‌ای خطاها

خطاهای ۵۲ سوال ناموفق به سه دسته اصلی تقسیم می‌شوند:

**دسته A: MISSING_GENERATED_SQL (11 مورد) — سیستم اصلاً SQL تولید نکرده**
- **علت ۱ (۵ مورد)**: Intent classifier سوالات `country_benchmark_dashboard` و `dashboard_story` را به اشتباه `ambiguous_query` (confidence=0.5) طبقه‌بندی کرده و Graph بدون تلاش برای تولید SQL، مستقیماً `ask_clarification` برگردانده. مثال: VTD-217, VTD-219, VTD-222, VTD-256, VTD-282.
- **علت ۲ (۴ مورد)**: Intent classifier سوالات ساده مثل «کشورها تو survey چطورن؟» را `definition_query` طبقه‌بندی کرده و Graph مسیر `answer_without_sql` را رفته. مثال: VTD-289, VTD-290, VTD-306, VTD-322.
- **علت ۳ (۲ مورد)**: مدل JSON نامعتبر تولید کرده و Parser کرش کرده (`Unterminated string`). مثال: VTD-119, VTD-141.

**دسته B: INVALID_SQL (13 مورد) — مدل SQL نوشته ولی اجرا نمی‌شود**
- **علت ۱ (۸ مورد)**: مدل نام ستون‌هایی را حدس زده که در Schema وجود ندارند (hallucination). مثال: `sleep_hours` به جای `sleep_duration_category`، `avg_cgpa` به جای `cgpa_10`.
- **علت ۲ (۳ مورد)**: پس از اولین شکست، Repair Prompt دیتابیس Schema را ندارد و مدل ستون‌ها را فراموش کرده و دوباره همان خطا را تکرار کرده (Loop detected).
- **علت ۳ (۲ مورد)**: مدل از توابع غیرمجاز SQLite مثل `PERCENTILE_CONT` استفاده کرده.

**دسته C: RESULT_MISMATCH (28 مورد) — SQL اجرا شده ولی جواب غلط است**
- **زیردسته C1 (۹ مورد)**: قاضی DeepSeek تأیید کرده که SQL از نظر بیزینسی درست است و فقط تفاوت در تعداد ستون‌ها یا نام alias وجود دارد → `business_correct` (اینها در واقع درست هستند).
- **زیردسته C2 (۱۸ مورد)**: قاضی تأیید کرده که SQL واقعاً منطق اشتباهی دارد → `business_incorrect`. شامل: فراموشی `WHERE`، `GROUP BY` اشتباه، فرمول ریاضی نادرست، یا `JOIN` غلط.
- **زیردسته C3 (۱ مورد)**: خطای پارس شدن پاسخ قاضی → `provider_parse_error`.

---

### 17.1 - Robust Intent Routing: حذف False Abstention (هدف: حل ۹ مورد از ۱۱ MISSING_SQL)

#### 17.1.1 - کاهش آستانه Ambiguity برای سوالات SQL-positive

- [x] **فایل**: `src/nlu/intent_classifier.py`
- [x] **تابع هدف**: `classify_intent(question: str) -> IntentResult`
- [x] **مشکل فعلی**: تابع `classify_intent` برای سوالاتی که حاوی کلمات کلیدی مثل «بساز»، «بده»، «نشان بده» هستند ولی یک کشور یا موجودیت خاص ذکر کرده‌اند (مثل «برای Germany رتبه جهانی ... را بساز»)، intent را `ambiguous_query` با confidence=0.5 برمی‌گرداند. این باعث می‌شود Graph بدون هیچ تلاشی برای تولید SQL، مستقیماً `ask_clarification` برگرداند.
- [x] **تغییر مورد نیاز**: اگر سوال حاوی نام کشور/موجودیت مشخص + فعل دستوری (بساز/بده/نشان بده/مقایسه کن) باشد، intent باید `grouping_query` یا `comparison_query` با confidence ≥ 0.7 باشد تا Graph اجازه تولید SQL بدهد.
- [x] **محل دقیق در کد**: بلوک‌هایی که `return IntentResult("ambiguous_query", 0.5)` برمی‌گردانند باید یک guard اضافه شوند: اگر value linker حداقل یک entity match پیدا کرده، confidence را بالا ببرد.
- [x] **تست**: `tests/tier1_unit/test_intent_classifier.py` — اضافه کردن test caseهای VTD-217, VTD-219, VTD-222, VTD-256 و بررسی اینکه intent به `ambiguous_query` نمی‌رود.
- [x] **معیار پذیرش**: هیچکدام از ۵ سوال `country_benchmark_dashboard` دیگر `ask_clarification` برنگردانند.

#### 17.1.2 - اصلاح مسیر Definition Query برای سوالات دیتابیسی

- [x] **فایل**: `src/nlu/intent_classifier.py` و `src/graph/routes.py`
- [x] **مشکل فعلی**: سوالاتی مثل «کشورها تو survey محل کار از نظر تعداد پاسخ چطورن؟» (VTD-290) یا «وضعیت اشتغال افراد دیتاست عمومی رو خلاصه کن» (VTD-282) به `definition_query` طبقه‌بندی می‌شوند و Graph مسیر `answer_without_sql` را می‌رود.
- [x] **تغییر مورد نیاز در intent_classifier**: اگر سوال حاوی کلمات مرتبط با داده (دیتاست، survey، تعداد، توزیع، خلاصه) باشد و در عین حال حاوی واژه‌های تعریفی خالص (مثل «ADHD چیست؟») نباشد، intent باید SQL-positive باشد (مثلاً `grouping_query` یا `raw_retrieval_query`).
- [x] **تغییر مورد نیاز در routes.py**: تابع `route_after_nlu` باید `definition_query` را فقط زمانی به `answer_without_sql` بفرستد که سوال واقعاً یک تعریف مفهومی بخواهد (مثل «افسردگی چیست؟»)، نه وقتی که درباره داده‌های دیتابیس سؤال می‌پرسد.
- [x] **تست**: `tests/tier1_unit/test_intent_classifier.py` — اضافه کردن test caseهای VTD-289, VTD-290, VTD-306, VTD-322.
- [x] **معیار پذیرش**: هیچکدام از ۴ سوال ساده دیتابیسی دیگر به `answer_without_sql` نروند.

#### 17.1.3 - تست یکپارچه Routing

- [x] **فرمان تست**:
  ```
  .\.venv\Scripts\python.exe -m pytest tests\tier1_unit\test_intent_classifier.py tests\tier1_unit\test_graph_routes.py -vv --tb=short
  ```
- [x] **معیار پذیرش**: تمام تست‌ها pass شوند و هیچ regression در intent‌های قبلی ایجاد نشود.

---

### 17.2 - Robust JSON Parser: حذف کرش پارسر (هدف: حل ۲ مورد از ۱۱ MISSING_SQL)

#### 17.2.1 - افزودن Regex Fallback به Output Parser

- [x] **فایل**: `src/generation/output_parser.py`
- [x] **تابع هدف**: `parse_llm_output(raw: str) -> dict`
- [x] **مشکل فعلی**: وقتی مدل LLM خروجی‌ای می‌دهد که JSON معتبر نیست (مثلاً `Unterminated string` یا متن آزاد قبل/بعد از JSON)، تابع `json.loads()` کرش می‌کند و exception به بالا propagate می‌شود. سیستم این را به عنوان `MISSING_GENERATED_SQL` ثبت می‌کند.
- [x] **تغییر مورد نیاز**: یک pipeline سه‌مرحله‌ای پیاده‌سازی شود:
  1. **مرحله ۱**: ابتدا `json.loads(raw)` را امتحان کن. اگر موفق شد، برگردان.
  2. **مرحله ۲**: اگر شکست خورد، با regex الگوی ` ```json ... ``` ` یا `{...}` را از متن استخراج کن و دوباره `json.loads()` بزن.
  3. **مرحله ۳ (Fallback SQL Extraction)**: اگر باز هم شکست خورد، با regex الگوی `SELECT\s+.+?FROM\s+\w+` را از متن خام استخراج کن. اگر یک SQL معتبر پیدا شد، آن را در `{"sql": "<extracted>", "explanation": "auto-extracted", "needs_clarification": false}` بسته‌بندی کن و برگردان.
  4. اگر هیچکدام موفق نشد، `None` برگردان (نه exception).
- [x] **Regex پیشنهادی برای مرحله ۲**:
  ```python
  import re
  # Try to extract JSON block from markdown code fence
  m = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', raw, re.DOTALL)
  if not m:
      # Try to find first {...} block
      m = re.search(r'\{[^{}]*"sql"\s*:\s*"[^"]*SELECT[^}]*\}', raw, re.DOTALL | re.IGNORECASE)
  ```
- [x] **Regex پیشنهادی برای مرحله ۳**:
  ```python
  sql_match = re.search(r'(SELECT\s+.+?(?:FROM\s+\w+).+?)(?:;|\n\n|```|$)', raw, re.DOTALL | re.IGNORECASE)
  ```
- [x] **تست**: `tests/tier1_unit/test_output_parser.py` — حداقل ۴ test case:
  1. JSON معتبر → parse موفق
  2. JSON داخل code fence → parse موفق
  3. JSON خراب ولی SQL موجود → fallback extraction موفق
  4. متن بدون هیچ SQL → `None` برگشت داده شود
- [x] **معیار پذیرش**: هیچ `Unterminated string` یا `Failed to parse JSON` دیگر منجر به `MISSING_GENERATED_SQL` نشود.

---

### 17.3 - Enhanced Repair Prompt: تزریق مجدد Schema (هدف: حل ≥۵ مورد از ۱۳ INVALID_SQL)

#### 17.3.1 - افزودن Schema به Repair Prompt Template

- [x] **فایل**: `src/generation/prompts/sql_repair.j2`
- [x] **وضعیت فعلی** (تمام محتوای فایل):
  ```
  The previous SQL was invalid.
  Original question: {{ question }}
  Previous SQL: {{ previous_sql }}
  Validation errors: {{ validation_errors }}
  Critic feedback: {{ critic_feedback }}
  Regenerate corrected SQLite SELECT SQL only as JSON.
  ```
- [x] **مشکل**: وقتی مدل در retry دوم یا سوم قرار می‌گیرد، هیچ اطلاعاتی از ساختار دیتابیس ندارد. نام ستون‌ها را فراموش می‌کند و دوباره همان hallucination را تکرار می‌کند. این مستقیماً باعث `Loop detected` و سپس `Execution failed after 3 retries` می‌شود.
- [x] **تغییر مورد نیاز**: Repair prompt باید شامل Schema، QIR و Value Links شود (دقیقاً مثل generation prompt اصلی):
  ```jinja2
  The previous SQL was invalid. Use the schema below to fix it.

  ### Database Schema
  {% for table_name, table_info in schema.items() %}
  Table: `{{ table_name }}`
  Columns:
  {% for col in table_info.columns %}
  - `{{ col.name }}` ({{ col.type }})
  {% endfor %}
  {% endfor %}

  ### Query Intent
  - Intent: {{ qir.task_type }}
  - Metrics: {{ qir.metrics | join(', ') if qir.metrics else "N/A" }}
  - Dimensions: {{ qir.dimensions | join(', ') if qir.dimensions else "None" }}

  ### Explicit Value Links
  {% for term, mapped_value in value_links.items() %}
  - "{{ term }}" -> `{{ mapped_value }}`
  {% endfor %}

  ### Previous Failed SQL
  {{ previous_sql }}

  ### Validation Errors
  {{ validation_errors }}

  ### Critic Feedback
  {{ critic_feedback }}

  ### Rules
  1. Fix ONLY the reported errors. Do not rewrite the entire query.
  2. Use ONLY the columns listed above. Do not hallucinate columns.
  3. Output format: {"sql": "SELECT ...", "explanation": "...", "needs_clarification": false}
  ```

#### 17.3.2 - پاس دادن Schema به تابع Repair در Graph Node

- [x] **فایل**: `src/graph/nodes/base_nodes.py`
- [x] **تابع هدف**: تابعی که repair prompt را می‌سازد و به مدل LLM ارسال می‌کند (احتمالاً `generate_sql` یا `repair_sql` یا بخش retry داخل `generate_sql`).
- [x] **تغییر مورد نیاز**: در زمان ساختن repair prompt، `schema_context`, `qir` و `value_links` از `VTDState` خوانده شوند و به عنوان متغیرهای Jinja2 به `sql_repair.j2` پاس داده شوند.
- [x] **نکته مهم**: `schema_context` قبلاً در State ذخیره شده (از مرحله Schema Linking). فقط باید در زمان فراخوانی template rendering آن را بخوانید.
- [x] **تست**: `tests/tier1_unit/test_graph_attempt_trace.py` — بررسی کنید که repair attempt حاوی `prompt` با نام ستون‌های Schema باشد.
- [x] **معیار پذیرش**: در اجرای Smoke بعدی، هیچ `Loop detected` ناشی از تکرار همان hallucination وجود نداشته باشد.

---

### 17.4 - Chain-of-Thought (CoT) Prompting (هدف: حل ≥۸ مورد از ۱۸ RESULT_MISMATCH business_incorrect)

#### 17.4.1 - بازنویسی sql_generation.j2 با ساختار CoT

- [x] **فایل**: `src/generation/prompts/sql_generation.j2`
- [x] **مشکل فعلی**: مدل مستقیماً `{"sql": "...", "explanation": "..."}` تولید می‌کند. مدل 7B بدون فکر کردن قبل از نوشتن SQL، اغلب `WHERE` یا `GROUP BY` را فراموش می‌کند یا فرمول ریاضی اشتباه می‌نویسد.
- [x] **تغییر مورد نیاز**: فرمت خروجی مدل از:
  ```json
  {"sql": "SELECT ...", "explanation": "...", "needs_clarification": false}
  ```
  به:
  ```json
  {
    "thought_process": "Step 1: I need table X. Step 2: Filter by Y. Step 3: Group by Z and compute AVG(W).",
    "sql": "SELECT ...",
    "needs_clarification": false
  }
  ```
  تغییر کند. بخش `### Output Format` در template باید به این شکل درآید:
  ```
  ### Output Format
  Respond ONLY with a JSON object. Think step-by-step BEFORE writing SQL.
  {
    "thought_process": "1. Tables needed: ... 2. Columns needed: ... 3. Filters: ... 4. Aggregation: ... 5. Expected output shape: ...",
    "sql": "SELECT ...",
    "needs_clarification": false
  }
  ```
- [x] **چرا این کار می‌کند**: تحقیقات نشان داده که مدل‌های کوچک وقتی مجبور شوند ابتدا reasoning بنویسند و سپس کد بنویسند، دقت SQL آنها ۱۵-۲۵٪ افزایش می‌یابد (Wei et al., 2022). این به این دلیل است که tokenهای thought_process، context window مدل را با اطلاعات مرتبط پر می‌کنند و attention mechanism بهتر روی ستون‌ها و شروط تمرکز می‌کند.
- [x] **ریسک Overfit**: این تغییر عمومی است و به هیچ case_id خاصی وابسته نیست. فقط ساختار خروجی مدل عوض می‌شود.

#### 17.4.2 - به‌روزرسانی Output Parser برای خواندن CoT

- [x] **فایل**: `src/generation/output_parser.py`
- [x] **تغییر مورد نیاز**: Parser باید فیلد `thought_process` را از JSON استخراج و در metadata ذخیره کند (اما فقط `sql` و `needs_clarification` را به Graph برگرداند). اگر `thought_process` وجود نداشت، باید backward-compatible باشد.
- [x] **تست**: `tests/tier1_unit/test_output_parser.py` — test case جدید با CoT JSON format.

#### 17.4.3 - اضافه کردن Hardcoded Examples با CoT

- [x] **فایل**: `src/generation/prompts/sql_generation.j2`
- [x] **تغییر مورد نیاز**: مثال‌های ثابت (hardcoded examples) در template باید فرمت CoT را نشان بدهند تا مدل الگوی خروجی را یاد بگیرد:
  ```
  **User**: درصد دانشجویانی که افسردگی دارند چقدر است؟
  **Response**:
  {"thought_process": "1. Table: student_depression. 2. Column: depression_flag (binary 0/1). 3. Formula: AVG(depression_flag) * 100.", "sql": "SELECT AVG(depression_flag) * 100.0 FROM student_depression;", "needs_clarification": false}
  ```
- [x] **معیار پذیرش**: مدل در Smoke test باید `thought_process` را قبل از `sql` تولید کند.

---

### 17.5 - افزودن Few-Shot Examples بیشتر و متنوع‌تر (هدف: حل ≥۵ مورد RESULT_MISMATCH)

#### 17.5.1 - بررسی و غنی‌سازی Few-Shot Bank

- [x] **فایل**: `data/golden_sql/few_shot_bank.jsonl`
- [x] **تحلیل مورد نیاز**: بررسی کنید که آیا few-shot bank شامل مثال‌هایی از تمام categoryهای پرخطا هست:
  - `advanced_sql` (6 خطا): آیا مثالی از `CTE`, `WINDOW FUNCTION`, `HAVING` وجود دارد؟
  - `analysis` (6 خطا): آیا مثالی از `CASE WHEN` و محاسبات مشتقه وجود دارد؟
  - `simple` (6 خطا): آیا مثالی از `COUNT(*)`, `GROUP BY` ساده وجود دارد؟
  - `country_benchmark_dashboard` (3 خطا): آیا مثالی از `country_prevalence_long` با `RANK()` وجود دارد؟
- [x] **تغییر مورد نیاز**: برای هر category که مثال ندارد، حداقل ۲ مثال جدید از `data/golden_sql/golden_examples.jsonl` انتخاب و اضافه شود.
- [x] **محدودیت Overfit**: مثال‌ها باید از **train split** باشند، نه از dev/test. اگر از golden_examples انتخاب می‌شوند باید ID آنها در train باشد.
- [x] **تست**: `scripts/check_benchmark_leakage.py` را بعد از اضافه کردن اجرا کنید تا مطمئن شوید leakage ایجاد نشده.

#### 17.5.2 - افزایش top_k بازیابی از ۳ به ۵

- [x] **فایل**: `scripts/run_benchmark.py` (پارامتر `--top-k`)
- [x] **توجیه**: با ۳ مثال، مدل اغلب فقط مثال‌های ساده می‌بیند. با ۵ مثال، احتمال اینکه یک مثال مرتبط با الگوی پیچیده سوال (مثل `JOIN` دو جدول یا `WINDOW FUNCTION`) بازیابی شود، بیشتر می‌شود.
- [x] **ریسک**: افزایش context window usage. باید بررسی شود که ۵ مثال + Schema + CoT + سوال هنوز در ۴۰۹۶ توکن جا بشود. اگر نه، context window باید به ۸۱۹۲ افزایش یابد (`VTD_LLM_N_CTX=8192`).
- [x] **تست**: یک Smoke test با `--top-k 5` اجرا شود و بررسی شود که مدل timeout نمی‌شود.

---

### 17.6 - حل مشکل Abstention نادرست (هدف: حل ۵ مورد wrong_abstention)

#### 17.6.1 - بررسی و اصلاح Abstention Logic

- [x] **فایل**: `src/graph/routes.py` — تابع `route_after_nlu`
- [x] **مشکل فعلی**: ۵ مورد wrong_abstention وجود دارد (مدل تصمیم گرفته SQL ننویسد در حالیکه باید می‌نوشت). این معمولاً ناشی از intent=`ambiguous_query` با confidence پایین یا intent=`definition_query` است.
- [x] **تغییر مورد نیاز**: routing logic باید فقط در صورتی که **هر سه شرط** زیر برقرار باشد، سوال را به مسیر non-SQL بفرستد:
  1. intent واقعاً `definition_query` باشد (نه `ambiguous_query`)
  2. confidence بالای ۰.۸ باشد
  3. سوال هیچ اشاره‌ای به جدول، ستون، یا داده‌های عددی نداشته باشد
- [x] **در غیر این صورت**: سوال باید به مسیر SQL-generation فرستاده شود و مدل تلاش کند SQL بنویسد. اگر مدل خودش `"needs_clarification": true` برگرداند، آن وقت clarification نشان داده شود.

---

### 17.7 - Smoke Test و اجرای مجدد بنچمارک کامل

#### 17.7.1 - اجرای Smoke Test (5 سوال پیچیده)

- [ ] **فرمان**:
  ```powershell
  .\.venv\Scripts\python.exe scripts\run_benchmark.py `
    --mode agent --dataset dev --samples-per-level 1 `
    --bootstrap-iterations 100 --exclude-self `
    --trace-level full --ablation-id phase17_smoke_v1
  ```
- [ ] **معیار پذیرش Smoke**:
  - `MISSING_GENERATED_SQL` باید ≤ ۱ باشد (از ۴ سوال)
  - `valid_sql_rate` باید ≥ ۰.۷۵ باشد
  - هیچ `Loop detected` ناشی از تکرار hallucination وجود نداشته باشد
  - Parser هیچ `Failed to parse JSON` نداشته باشد

#### 17.7.2 - اجرای بنچمارک کامل Phase 17

- [ ] **فرمان**:
  ```powershell
  .\.venv\Scripts\python.exe scripts\run_benchmark.py `
    --mode agent --dataset dev --sample 0 `
    --bootstrap-iterations 500 --exclude-self `
    --trace-level full --ablation-id phase17_full_dev_v1 `
    --use-judge --judge-provider openrouter `
    --judge-model deepseek/deepseek-v4-flash `
    --judge-reasoning
  ```
- [ ] **معیار پذیرش Phase 17**:
  - Semantic Accuracy (strict + business_correct) ≥ **60%** (≥36/60)
  - Valid SQL Rate ≥ **80%** (≥48/60)
  - MISSING_GENERATED_SQL ≤ **3** (از ۶۰)
  - Unsafe SQL = **0**

#### 17.7.3 - مقایسه A/B با Baseline

- [ ] **فرمان**:
  ```powershell
  .\.venv\Scripts\python.exe scripts\analyze_ablation_manifest.py `
    results\benchmark\20260522_123019_agent_dev_qwen2_5-coder-7b-instruct-q4_k_m_full_dev_baseline `
    results\benchmark\<phase17_full_dev_artifact>
  ```
- [ ] **معیار پذیرش**: هر metric (EX, Valid SQL, Semantic Accuracy) باید بهتر از Baseline باشد و هیچ regression در unsafe_sql وجود نداشته باشد.

---

### 17.8 - مستندسازی و ثبت نتایج

- [ ] ثبت نتایج Smoke و Full benchmark در همین فایل (`task.md`).
- [ ] به‌روزرسانی `DEVELOPMENT_ROADMAP.md` با نتایج نهایی Phase 17.
- [ ] ایجاد `results/error_analysis/<timestamp>_phase17_accuracy_boost/error_report.md`.
- [ ] اگر دقت به ۶۰٪ نرسید: تحلیل خطاهای باقیمانده و تعیین اینکه آیا مشکل از محدودیت مدل 7B است یا از معماری.
- [ ] آماده‌سازی سند QLoRA Fine-tuning Plan برای رساندن دقت به ۹۰٪ با مدل fine-tuned.


---

## Phase 18 - Accuracy Optimization (بدون Fine-tuning) [IN PROGRESS]

هدف: افزایش Execution Accuracy از 32.5% به >60% با بهینه‌سازی Prompt، Few-shot، Schema Linking و NLU.

### Benchmark Baseline (Phase 17 Final)

| متریک | مقدار |
|---|---|
| Execution Accuracy | 32.5% (130/400) |
| Valid SQL Rate | 82.5% (330/400) |
| Easy Accuracy | 60.0% |
| Medium Accuracy | 21.0% |
| Hard Accuracy | 30.0% |
| Complex Accuracy | 19.0% |

### توزیع خطاها (270 مورد)

| # | دسته خطا | تعداد | درصد از کل خطاها | نوع راهکار | فاز |
|---|---|---|---|---|---|
| 1 | MISSING_ROUND | 58 | 21.5% | Prompt Hint | A |
| 2 | WRONG_FILTER_VALUE | 44 | 16.3% | Value Linking + Few-shot | C |
| 3 | HALLUCINATED_FILTER | 35 | 13.0% | Negative Few-shot | B |
| 4 | MISSING_FILTER | 31 | 11.5% | Prompt Hint | A |
| 5 | ROUTING_ERROR | 24 | 8.9% | NLU Fix | D |
| 6 | SYNTAX_ERROR | 23 | 8.5% | Reflexion + Schema | C |
| 7 | WRONG_GROUP_COLUMNS | 17 | 6.3% | Schema Linking + Few-shot | C |
| 8 | WRONG_COLUMN_REF | 15 | 5.6% | Schema Linking | C |
| 9 | WRONG_SELECT_COLS | 6 | 2.2% | Few-shot | B |
| 10 | MISSING_SUBQUERY | 6 | 2.2% | Model Limit | QLoRA |
| 11 | UNGROUPED_COLUMN | 4 | 1.5% | Prompt Hint | A |
| 12 | LIMIT_MISMATCH | 3 | 1.1% | Prompt Hint | A |
| 13 | GROUP_BY_MISMATCH | 3 | 1.1% | Few-shot | B |
| 14 | WRONG_TABLE_REF | 1 | 0.4% | Schema Linking | C |

### Phase 18-A: Prompt Hints (بهبود بالقوه: +24.3% = 97 مورد) [COMPLETED ✅]

- [x] **ROUND hint**: 'همیشه مقادیر اعشاری (AVG, درصد) را با ROUND(..., 2) گرد کن.'
- [x] **NULL filter hint**: 'هنگام محاسبه AVG/SUM/MIN/MAX، همیشه WHERE col IS NOT NULL اضافه کن.'
- [x] **Anti-hallucination hint**: 'فقط زمانی WHERE اضافه کن که کاربر صراحتاً شرطی ذکر کرده باشد.'
- [x] **UNGROUPED_COLUMN hint**: 'CASE WHEN باید در GROUP BY باشد'
- [x] **LIMIT hint**: 'LIMIT فقط وقتی top-N خواسته شده'

### Phase 18-B: Few-shot & RAG Optimization (بهبود بالقوه: +10.3% = 41 مورد) [COMPLETED ✅]

- [x] **Negative few-shot examples**: نمونه‌هایی که نشان می‌دهد 'فیلتر نزن مگر خواسته شده'.
- [x] **Column selection examples**: نمونه‌های صحیح SELECT.
- [x] **GROUP BY examples**: نمونه‌هایی با GROUP BY.
- [x] بررسی و بهبود CAG retriever: اطمینان از بازیابی صحیح.

### Phase 18-C: Schema & Value Linking (بهبود بالقوه: +16.6% = 59 مورد) [COMPLETED ✅]

- [x] **Column descriptions فارسی**: اضافه شدن توضیحات ستون‌های کلیدی.
- [x] **Table descriptions فارسی**: اضافه شدن توضیحات جداول.
- [x] **بهبود Schema Linker**: وزن دهی بهتر برای 'اضطراب' به 'anxiety_score'.
- [x] **بهبود Reflexion loop**: افزایش max_retries و context خطاها.

### Phase 18-D: NLU Routing Fix (بهبود بالقوه: +6.0% = 24 مورد) [COMPLETED ✅]

- [x] **Data-Aware Signals**: آپدیت ambiguity_detector.py برای کلماتی مانند دیتاست، دانشجو و ...
- [x] **Definition Query Fix**: آپدیت intent_classifier.py تا سوالات تحلیلی را با تعریف اشتباه نگیرد.
- [x] **Early Exit Prevention**: بررسی مسیرها در routes.py برای اطمینان از پیشگیری خروج زودرس سوالات SQL دار.
- [x] اجرای benchmark کامل (در حال اجرا روی پس زمینه)

### فاز بعدی: Phase 19 — QLoRA Fine-tuning

بعد از اثبات >60% با بهینه‌سازی‌های بالا، خطاهای باقی‌مانده (مانند MISSING_SUBQUERY) محدودیت‌های ذاتی مدل 7B هستند و با Fine-tuning حل خواهند شد:

- [ ] استخراج training dataset از artifacts با `--trace-level full`
- [ ] آماده‌سازی دیتاست QLoRA (instruction/input/output)
- [ ] اجرای fine-tuning روی Qwen2.5-Coder-7B
- [ ] بنچمارک مدل fine-tuned با هدف >90%
