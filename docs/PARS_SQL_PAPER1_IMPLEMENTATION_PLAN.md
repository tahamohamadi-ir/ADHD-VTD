# برنامه اجرایی مقاله اول PARS-SQL / VTD

این سند برنامه عملیاتی کامل برای تبدیل کد فعلی پروژه `ADHD-VTD` به یک artifact پژوهشی قابل چاپ برای مقاله اول است. هدف سند این است که یک نفر دیگر، بدون دانستن تاریخچه گفتگوها، بتواند کار را مرحله به مرحله اجرا کند، خروجی‌ها را بسازد، صحت آن‌ها را بسنجد و در نهایت جدول‌ها و شواهد لازم برای مقاله را تولید کند.

تاریخ بازبینی کدبیس: `2026-06-26`  
مسیر پروژه: `D:\Project\ADHD-VTD`  
دامنه مقاله اول: Persian-aware, reliability-first, local/private Text-to-SQL برای داده‌های سلامت روان و سبک زندگی.

منابعی که این نسخه با آن‌ها ادغام شده است:

```text
task.md
C:\Users\Taha\Downloads\paper1_implementation_plan.md
docs/phases/PHASE_18_7_ZERO_SHOT_MASTERY.md
docs/06_EVALUATION_ABLATION_AND_PAPER_PLAN.md
docs/07_IMPLEMENTATION_ROADMAP_AND_REQUIREMENTS.md
```

نکته مهم: فایل دانلودی `paper1_implementation_plan.md` بیشتر حالت «از صفر چه بسازیم» دارد. این سند آن برنامه را با وضعیت واقعی repo ادغام می‌کند. بنابراین هرجا کد فعلی از قبل وجود دارد، اقدام درست «تثبیت، تست، artifact کردن و تکمیل contract» است، نه دوباره‌نویسی.

---

## 0. وضعیت فعلی در 2026-06-22

این بخش پاسخ مستقیم به این سؤال است: «الان دیگر چه مانده؟»

### بسته شده و artifact-backed است

- **B0 کامل است**: dataset contract، trace contract، parse failure hardening، graph routing، safety/privacy gate و reranker CLI contract بسته شده‌اند.
- **B1.1 Gold SQL closeout کامل است**:
  - Artifact: `results/benchmark/20260621_064906_gold_positive400_qwen2-5-coder-7b_paper1_gold_positive400`
  - نتیجه: `400/400`, `execution_accuracy=1.0`, `valid_sql_rate=1.0`, `failures=0`.
- **B1.2 Full behavior_test کامل است**:
  - Artifact: `results/benchmark/20260621_072711_agent_behavior_test_qwen2-5-coder-7b_paper1_behavior_test_b1_2_actionfix`
  - نتیجه: `expected_action_accuracy=52/60=0.8667`, `safety_rejection_accuracy=1.0`, `abstention_recall=1.0`, `unsafe_sql=0`.
- **B1.3 full local no-template کامل و artifact-backed است**:
  - Artifact smoke: `results/benchmark/20260621_073923_agent_positive400_qwen2-5-coder-7b_paper1_main_local_no_templates_smoke`
  - نتیجه smoke: `execution_accuracy=3/5=0.6`, `valid_sql_rate=1.0`, `deterministic_templates=false`.
  - Artifact diagnostic full attempt: `results/benchmark/20260621_104339_agent_positive400_qwen2-5-coder-7b_paper1_main_local_no_templates`
  - نتیجه diagnostic: بعد از `9/400` متوقف شد، چون config پیش‌فرض با `max_retries=5` روی failureهای average وارد repair/reflexion loopهای طولانی می‌شد. این artifact فقط diagnostic است و نباید به‌عنوان result مقاله گزارش شود.
  - Config جدید full: `experiments/configs/paper1_main_local_no_templates_bounded.yaml`
  - Artifact bounded smoke نهایی: `results/benchmark/20260621_112756_paper1_main_local_no_templates_bounded_smoke`
  - نتیجه bounded smoke: `sample=10`, `execution_accuracy=4/10=0.4`, `valid_sql_rate=10/10=1.0`, `max_retries=1`, `max_retries_source=config`, `trace_contract.validated=true`, `ablation_runtime_contract.warnings=[]`.
  - Artifact full نهایی: `results/benchmark/20260621_122748_paper1_main_local_no_templates_bounded`
  - نتیجه full: `total_evaluated=400`, `execution_accuracy=102/394=0.2589`, `valid_sql_rate=295/394=0.7487`, `failures=298`, `max_retries=1`, `deterministic_templates=false`, `trace_contract.validated=true`.
- **B1.4 Retrieval R0-R3 روی full dev کامل است**:
  - Manifest: `results/ablation/paper1_retrieval_final_dev_full/ablation_manifest.json`
  - نتیجه: هر چهار run روی `60` dev case، `failures=0`, `retrieval_hit_rate=1.0`, `trace_contract.validated=true`.
- **Tier 1 سبز است**:
  - آخرین نتیجه کامل: `411 passed, 3 warnings`.
  - تست targeted بعد از bounded retry config: `41 passed` برای `test_benchmark_runtime_config.py`, `test_graph_retry_and_config.py`, `test_reliability_gate.py`.

### هنوز مانده و برای paper claim لازم است

1. **B1.3 full local no-template run روی positive400**  
   انجام شده و artifact-backed است. حالا باید به‌عنوان main local result گزارش شود، اما عدد آن پایین است و باید صادقانه با error analysis و limitations همراه شود.

2. **B1.5 ablation اصلی A0-A4/A7**  
   A0-A4/A7 علاوه بر 8-case smoke و full-dev bounded، اکنون روی full positive400 هم اجرا و تحلیل شده است. نتیجه اصلی ablation مقاله باید full positive400 باشد و full-dev فقط evidence توسعه‌ای/تأییدی است.

3. **Full behavioral100 اگر ادعای کل behavioral set می‌کنی**  
   `behavior_test=60` و `behavior_dev=40` هر دو کامل اجرا شده‌اند. مجموع behavioral100: `expected_action_accuracy=76/100=0.76`, `safety_rejection_accuracy=16/16=1.0`, `clarification_accuracy=22/25=0.88`, `abstention_precision=80/90=0.8889`, `abstention_recall=80/83=0.9639`, `unsafe_sql=0`. این کامل است، اما expected-action زیر target پیشنهادی 80% است.

4. **Semantic/business judge full audit**  
   OpenRouter judge اکنون روی همه 400 prediction اصلی اجرا و merge شده است. Artifact نهایی: `results/judgments/paper1_main_semantic_openrouter_s400_split/merged_authoritative`. نتیجه: `authoritative=true`, `authoritative_judgments=400`, `business_correct=161/400=0.4025`, `business_incorrect=239/400=0.5975`, `provider_error=0`, `provider_parse_error=0`, `redaction_applied=true`. این metric باید جدا از strict execution accuracy گزارش شود.

5. **Error analysis و representative failures**  
   گزارش اصلی ساخته شده: `results/error_analysis/paper1_main_local_bounded/error_report.md`. برای paper package نهایی فقط باید خلاصه representative failureها وارد `results/reports/` شود.

6. **Final report package**  
   `paper_tables.md`, `paper_metrics.csv`, `final_artifact_manifest.json`, `PARS_SQL_PAPER1_RESULTS_SUMMARY.md` نهایی و `PARS_SQL_PAPER1_REPRODUCIBILITY.md` باید از artifact نهایی بازسازی شوند.

7. **Clean paraphrase holdout برای claim ضد overfit**  
   اگر مقاله بخواهد claim قوی ضد overfit بدهد، یک holdout/paraphrase مستقل لازم است. اگر نه، باید محدودیت split/debug leakage صریح گزارش شود.

### داکیومنت‌های تازه/به‌روز برای ادامه

```text
docs/DATASET_CARD.md
docs/PARS_SQL_PAPER1_RESULTS_SUMMARY.md
docs/PARS_SQL_PAPER1_REPRODUCIBILITY.md
docs/paper/limitations.md
```

این فایل‌ها وضعیت فعلی را ثبت می‌کنند، اما report package نهایی نیستند. بعد از ablation بزرگ‌تر B1.5 و semantic/human judge قابل‌اتکا باید دوباره به‌روزرسانی شوند.

Configهای اضافه‌شده برای ادامه B1.3:

```text
experiments/configs/paper1_main_local_no_templates_bounded.yaml
experiments/configs/paper1_main_local_no_templates_bounded_smoke.yaml
```

---

## 1. خروجی نهایی مورد انتظار

در پایان این برنامه باید این خروجی‌ها وجود داشته باشند:

```text
docs/
  DATASET_CARD_DRAFT.md یا DATASET_CARD.md
  PARS_SQL_PAPER1_REPRODUCIBILITY.md
  PARS_SQL_PAPER1_RESULTS_SUMMARY.md

data/questions/
  full/vtd_question_sql_400_merged_validated.json
  special/vtd_evaluation_special_100.json
  holdout/ یا paraphrase_holdout/  # اگر holdout مستقل ساخته شود

results/benchmark/
  <final_gold_run>/
  <final_retrieval_runs>/
  <final_agent_ablation_runs>/
  <final_behavior_runs>/
  <final_judge_subset_run>/

results/ablation/
  <final_ablation_manifest>/
  ablation_comparison.md
  ablation_comparison.json

results/error_analysis/
  <final_error_analysis>/
  error_report.md
  representative_failures.md

results/reports/
  paper_tables.md
  paper_metrics.csv
  reliability_metrics.csv
  schema_value_linking_metrics.csv
  behavioral_metrics.csv
```

مقاله نباید فقط روی یک عدد `EX` بنا شود. باید نشان بدهد سیستم:

- روی SQL-positive examples خروجی قابل اجرا می‌دهد.
- روی behavioral examples می‌داند چه زمانی SQL نسازد.
- خطاهای schema/value linking، validation، retrieval، generation و reliability را جدا گزارش می‌کند.
- با مدل محلی و بدون تکیه به مدل cloud به عنوان هسته اصلی اجرا می‌شود.
- هر claim آن از یک artifact واقعی در `results/` قابل ردیابی است.

---

## 2. وضعیت فعلی کدبیس

این پروژه از صفر شروع نمی‌شود. فایل‌های زیر همین حالا وجود دارند و باید تکمیل/تثبیت شوند، نه اینکه دوباره ساخته شوند:

```text
scripts/run_benchmark.py
scripts/run_ablation.py
scripts/build_rag_index.py
scripts/judge_benchmark_artifact.py

src/graph/workflow.py
src/graph/state.py
src/graph/nodes/base_nodes.py
src/graph/routes.py

src/nlu/persian_normalizer.py
src/nlu/intent_classifier.py
src/nlu/safety_intent_detector.py
src/nlu/ambiguity_detector.py

src/schema/schema_linker.py
src/schema/value_linker.py
src/schema/query_planner.py
src/schema/schema_graph.py

src/retrieval/hybrid_retriever.py
src/retrieval/context_builder.py
src/retrieval/retrieval_scorer.py
src/retrieval/retrieval_metrics.py

src/generation/local_llm.py
src/generation/prompt_builder.py
src/generation/output_parser.py
src/generation/template_sql.py

src/sql_validation/validation_pipeline.py
src/sql_validation/safety_validator.py
src/sql_validation/schema_validator.py
src/sql_validation/join_validator.py
src/sql_validation/aggregation_validator.py
src/sql_validation/shape_validator.py

src/db/read_only_executor.py

src/evaluation/dataset_loader.py
src/evaluation/metrics.py
src/evaluation/reliability_metrics.py
src/evaluation/reliability_gate.py
src/evaluation/error_analyzer.py
src/evaluation/export_utils.py
src/evaluation/llm_judge.py
src/evaluation/statistical_tests.py
src/evaluation/artifact_analysis.py
```

وضعیت پژوهشی فعلی که باید در برنامه لحاظ شود:

- `Phase 0` و audit اولیه 50Q انجام شده و artifactهای آن در `data/questions/audit/` موجود است.
- dataset اصلی `positive400` و behavioral `special100` موجود است.
- benchmark runner سه mode اصلی دارد: `gold`, `retrieval`, `agent`.
- ablation runner وجود دارد و dry-run را از execution واقعی جدا می‌کند.
- reliability gate، judge، multi-candidate policy و error analysis وجود دارند اما باید برای claim مقاله gate شوند.
- طبق `task.md` و `PHASE_18_7_ZERO_SHOT_MASTERY.md`، نتیجه template-driven با `94.25%` نباید claim اصلی مقاله شود، چون template pack قرنطینه شده و overfit risk دارد.

---

## 3. اصل‌های غیرقابل مذاکره

این قوانین در کل برنامه باید رعایت شوند:

1. هیچ metric بدون artifact واقعی در `results/benchmark/` قابل گزارش نیست.
2. هیچ runtime logic نباید case id، gold SQL، یا لیست failureهای قبلی را برای تصمیم‌گیری استفاده کند.
3. `deterministic_templates=false` باید default مقاله باشد. templateها فقط به عنوان ablation/debug baseline گزارش شوند.
4. همه runهای قابل گزارش روی `positive400` باید `--exclude-self` داشته باشند.
5. اگر positive `test/` قبلاً در debug subsets استفاده شده باشد، برای claim نهایی باید holdout/paraphrase مستقل ساخته شود.
6. behavioral examples وارد denominator مربوط به `EX` نشوند.
7. SQL execution correctness و semantic/business correctness جدا گزارش شوند.
8. safety و read-only execution هیچ‌وقت ablation-disabled نشوند.
9. cloud judge فقط برای de-identified/synthetic artifact یا subset قضاوت استفاده شود و هسته سیستم نباشد.
10. خروجی benchmark باید prompt، raw model response، parsed payload، validation errors، execution status و final action را trace کند.

---

## 4. نقشه فازها

ترتیب اجرا:

```text
P0  Repo and contract freeze
P1  Dataset governance and audit closeout
P2  Critical code-contract fixes
P3  Benchmark artifact contract hardening
P4  NLU, schema linking, value linking metrics
P5  Retrieval/CAG ablation
P6  Local generation and model reproducibility
P7  Reliability and behavioral evaluation
P8  Ablation matrix A0-A7/A8
P9  Semantic/business judge full audit
P10 Error analysis and paper tables
P11 Reproducibility package and paper-ready closeout
```

هر فاز پایین شامل هدف، فایل‌های درگیر، کارهای اجرایی، commandها، و معیار پذیرش است.

---

## P0. Repo and Contract Freeze

### هدف

قبل از تغییرات فنی، باید قرارداد پژوهشی و وضعیت repo قفل شود تا بعداً معلوم باشد هر metric از چه نسخه‌ای آمده است.

### فایل‌های درگیر

```text
DEVELOPMENT_ROADMAP.md
task.md
docs/00_INDEX.md
docs/BENCHMARK_AND_TEST_GUIDE.md
docs/phases/PHASE_18_7_ZERO_SHOT_MASTERY.md
experiments/configs/*.yaml
scripts/run_benchmark.py
scripts/run_ablation.py
```

### کارها

1. یک branch یا commit مرجع برای شروع paper run بساز.
2. وضعیت dirty worktree را ثبت کن، اما تغییرات user را revert نکن.
3. در `task.md` یک section جدید اضافه کن: `Paper 1 Evidence Freeze`.
4. در آن section این موارد را ثبت کن:
   - آخرین artifact baseline قابل قبول.
   - artifactهایی که فقط debug/overfit هستند و نباید claim شوند.
   - مدل اصلی local برای paper run.
   - datasetهایی که برای paper استفاده می‌شوند.
   - datasetهایی که فقط debug هستند.

### Commandها

```powershell
cd D:\Project\ADHD-VTD
git status --short
git rev-parse --short HEAD
```

### معیار پذیرش

- یک commit hash یا snapshot id در گزارش‌ها ثبت شده باشد.
- مشخص باشد `phase18_7b5_template_pack154_validatorfix_full400` فقط ablation/debug است، نه main result.
- برای هر experiment، `config_id`, `ablation_id`, `dataset_hash`, `selected_cases_hash`, `model_path`, `enabled_modules`, `disabled_modules` در artifact ثبت شود.

---

## P1. Dataset Governance and Audit Closeout

### هدف

مقاله اول بدون benchmark تمیز قابل دفاع نیست. باید datasetها دقیقاً به سه نقش جدا تقسیم شوند:

- SQL-positive برای `EX` و valid SQL.
- behavioral برای abstention/refusal/clarification.
- holdout/paraphrase برای anti-overfit validation.

### وضعیت فعلی

فایل‌های موجود:

```text
data/questions/full/vtd_question_sql_400_merged_validated.json
data/questions/special/vtd_evaluation_special_100.json
data/questions/full/vtd_total_500_dataset_package.json
data/questions/train/train.json
data/questions/dev/dev.json
data/questions/test/test.json
data/questions/audit/phase0_50q_audit_cases.json
data/questions/audit/phase0_50q_audit_results.jsonl
```

طبق audit قبلی:

- `train/dev/test` با `280/60/60`، `full400` را بازسازی می‌کنند.
- `behavior_dev/behavior_test` با `40/60`، behavioral100 را بازسازی می‌کنند.
- `vtd_total_500_dataset_package` package است، holdout مستقل نیست.
- subsetهای `phase18_7b_failed154`, `phase18_7c0_failed266`, `phase18_7c0_lost119` فقط debug هستند.
- چون failure subsets شامل تعدادی از test cases بوده‌اند، `test/` برای final anti-overfit claim پاک نیست.

### فایل‌هایی که باید بررسی/تکمیل شوند

```text
src/evaluation/dataset_loader.py
scripts/validate_dataset.py
scripts/validate_dataset_sql.py
scripts/check_duplicate_questions.py
scripts/check_benchmark_leakage.py
scripts/check_schema_column_references.py
docs/DATASET_CARD_DRAFT.md
data/audit/vtd_400_500_audit_report.md
```

### کارهای اجرایی

1. dataset card را نهایی کن:
   - داده تشخیصی/clinical decision نیست.
   - فقط برای aggregate analytics است.
   - SQL-positive و behavioral جدا هستند.
   - gold SQLها validated هستند.
   - limitationهای Persian/Finglish/Jalali ذکر شوند.

2. همه SQLهای gold را validate و execute کن:
   - `positive400`
   - `train/dev/test`
   - `phase0`
   - `behavior100` فقط برای مواردی که `expected_sql` دارند.

3. leakage را بررسی کن:
   - duplicate normalized question بین train/dev/test.
   - self-overlap retrieval.
   - overlap بین debug subsets و final holdout.

4. اگر برای paper نیاز به holdout تمیز داری:
   - یک `data/questions/holdout/paraphrase_holdout_100.json` بساز.
   - نباید از failure IDs قبلی ساخته شود.
   - باید شامل paraphraseهای فارسی، typo، Finglish، colloquial و Jalali باشد.
   - gold SQLها باید مستقل audit شوند.

### Commandهای پیشنهادی

```powershell
.\.venv\Scripts\python.exe scripts\validate_dataset.py --path data\questions\full\vtd_question_sql_400_merged_validated.json
.\.venv\Scripts\python.exe scripts\validate_dataset_sql.py --path data\questions\full\vtd_question_sql_400_merged_validated.json
.\.venv\Scripts\python.exe scripts\check_duplicate_questions.py
.\.venv\Scripts\python.exe scripts\check_benchmark_leakage.py
.\.venv\Scripts\python.exe scripts\check_schema_column_references.py
```

اگر CLI بعضی از flagها را ندارد، اول script را فقط به اندازه همین نیاز توسعه بده؛ خروجی باید JSON/Markdown قابل ارجاع بسازد.

### معیار پذیرش

- همه gold SQLهای `positive400` اجرا شوند.
- `behavioral100` در denominator اجرای SQL وارد نشود.
- هر debug subset با برچسب `debug_only=true` یا در مستندات مشخص شود.
- dataset card حداقل این بخش‌ها را داشته باشد:
  - intended use
  - non-clinical disclaimer
  - schema/database version
  - annotation/audit protocol
  - split policy
  - leakage policy
  - behavioral expected actions
  - limitations

---

## P2. Critical Code-Contract Fixes

### هدف

قبل از runهای نهایی، چند ناهماهنگی عملی در کد باید رفع شود. این‌ها ممکن است در sampleهای خاص خطای graph، metric غلط یا artifact ناقص بسازند.

### Fix 1: مسیر `answer_without_sql`

در `src/graph/routes.py`، `route_pre_generation` ممکن است `answer_without_sql` برگرداند، اما در `src/graph/workflow.py` برای conditional edges فقط این mapping وجود دارد:

```text
link_schema
ask_clarification
refuse_unsafe_sql
```

### راه اصلاح

یکی از دو راه را انتخاب کن:

راه ترجیحی:

- node جدا اضافه کن: `answer_without_sql`.
- در workflow mapping اضافه کن.
- در `VTDState.actual_action` مقدار `answer_without_sql` ثبت شود.

راه ساده‌تر:

- `route_pre_generation` برای definition/chart advice همان `ask_clarification` را برگرداند.
- داخل `ask_clarification` همین حالا `actual_action` را به `answer_without_sql` یا `answer_chart_recommendation` تبدیل می‌کند.
- اسم node گمراه‌کننده می‌ماند، ولی graph نمی‌شکند.

### معیار پذیرش

```powershell
.\.venv\Scripts\python.exe -m pytest tests\tier1_unit\test_graph_routes.py tests\tier1_unit\test_intent_classifier.py -q
```

باید caseهای `definition_query`, `chart advice`, `unsafe`, `ambiguous`, `sql-positive` را پوشش بدهد.

### Fix 2: propagate کردن `safety_label` و دلایل routing

`IntentClassifier.classify` safety را بررسی می‌کند، اما state فعلی عمدتاً `intent`, `intent_confidence`, `should_generate_sql` را می‌گیرد. برای reliability و behavioral metrics باید این‌ها هم در state و prediction بیایند:

```text
safety_label
expected_action
intent_reasons
ambiguity_score
needs_clarification
```

### فایل‌ها

```text
src/nlu/intent_classifier.py
src/graph/nodes/base_nodes.py::classify_intent
src/graph/state.py
scripts/run_benchmark.py::agent_prediction
tests/tier1_unit/test_safety_detector.py
tests/tier1_unit/test_graph_state_reliability_fields.py
```

### معیار پذیرش

- unsafe request در prediction این fieldها را داشته باشد:
  - `intent=unsafe_query`
  - `safety_label != safe` یا reason معادل
  - `actual_action=refuse_unsafe_sql`

### Fix 3: parse failure نباید raw response را به عنوان SQL validate کند

در مسیر فعلی، اگر `parse_llm_output` JSON را parse نکند، فقط `validation_errors` برمی‌گرداند. اما `generated_sql` ممکن است هنوز raw model response باشد و بعداً به validator برسد.

### راه اصلاح

در `parse_llm_output`:

- اگر parse fail:
  - `generated_sql=None`
  - `parsed_payload=None`
  - یک `SQLAttempt` یا marker با `error_type=OUTPUT_PARSE_ERROR`
  - `needs_clarification=False`
- validator نباید raw LLM response را SQL فرض کند.

### فایل‌ها

```text
src/generation/output_parser.py
src/graph/nodes/base_nodes.py::parse_llm_output
src/graph/nodes/base_nodes.py::validate_sql
tests/tier1_unit/test_output_parser.py
tests/tier1_unit/test_graph_attempt_trace.py
```

### معیار پذیرش

- invalid JSON به `OUTPUT_PARSE_ERROR` تبدیل شود.
- attempts trace شامل raw response باشد.
- `valid_sql=false` و `generated_sql=null` در prediction ثبت شود.

### Fix 4: Schema linking result کامل وارد state شود

در `SchemaLinker.link` خروجی شامل `confidence`, `unresolved_terms`, `join_hints`, `evidence` است. در `base_nodes.link_schema` فعلاً بخشی از این‌ها از بین می‌روند و confidence ثابت `0.8` گذاشته می‌شود.

### راه اصلاح

در `link_schema`:

- `confidence=result.confidence`
- `unresolved_terms=result.unresolved_terms`
- `join_paths=result.join_hints`
- `schema_linking_evidence=result.evidence` در state یا `schema_context`
- اگر هیچ table پیدا نشد، fallback به `student_depression` فقط با warning و `low_confidence_fallback=true` ثبت شود.

### فایل‌ها

```text
src/graph/state.py
src/graph/nodes/base_nodes.py::link_schema
src/schema/schema_linker.py
tests/tier1_unit/test_schema_linker.py
tests/tier1_unit/test_graph_state_reliability_fields.py
```

### معیار پذیرش

- predictionها `linked_schema.confidence`, `unresolved_terms`, `join_paths` داشته باشند.
- schema fallback در artifact قابل شمارش باشد.

### Fix 5: Value linker باید چندمعنایی aliasها را از دست ندهد

در `src/schema/value_linker.py`، aliasهای دستی به صورت dict هستند. اگر یک کلید فارسی برای دو context مختلف لازم باشد، Python فقط آخرین مقدار را نگه می‌دارد. نمونه مهم: یک term مثل افسردگی ممکن است هم binary flag باشد، هم مقدار `disorder`.

### راه اصلاح

ساختار alias را از:

```python
MANUAL_ALIASES: dict[str, dict[str, object]]
```

به یکی از این دو تبدیل کن:

```python
MANUAL_ALIASES: list[ManualAliasSpec]
```

یا:

```python
MANUAL_ALIASES: dict[str, list[dict[str, object]]]
```

### معیار پذیرش

تست‌ها باید هر دو mapping را بپوشانند:

- `افسرده` / `depressed` برای `student_depression.depression_flag` به `1`.
- `افسردگی` برای `country_prevalence_long.disorder` به `depression`.

### Fix 6: CLI و docs برای reranker را همسو کن

در docs و phase plan، commandهایی با `--reranker` آمده‌اند، اما parser فعلی `scripts/run_benchmark.py` چنین flagی ندارد. یا باید flag اضافه شود، یا docs اصلاح شوند.

### راه ترجیحی

به `run_benchmark.py` اضافه کن:

```text
--reranker none|identity|bge-reranker-base|bge-reranker-v2-m3
```

و در config ثبت کن:

```text
retrieval_reranker
```

تا R3 واقعاً با reranker قابل ادعا باشد.

### معیار پذیرش

```powershell
.\.venv\Scripts\python.exe scripts\run_benchmark.py --mode retrieval --dataset dev --sample 5 --retrieval-backend hybrid --reranker identity --exclude-self
```

باید اجرا شود و config خروجی شامل `retrieval_reranker=identity` باشد.

---

## P3. Benchmark Artifact Contract Hardening

### هدف

هر benchmark باید خروجی کامل، قابل ردیابی و paper-ready بسازد.

### artifactهای الزامی

هر run در `results/benchmark/<run>/` باید حداقل این‌ها را داشته باشد:

```text
<prefix>_config.json
<prefix>_summary.json
<prefix>_summary.md
<prefix>_predictions.jsonl
<prefix>_attempts.jsonl
<prefix>_failures.jsonl
<prefix>_benchmark_results.csv
<prefix>_reliability_summary.csv
<prefix>_error_taxonomy.csv
<prefix>_paper_tables.md
```

اگر judge فعال است:

```text
<prefix>_judgments.jsonl
<prefix>_judge_summary.json
<prefix>_judge_costs.json
<prefix>_semantic_business_summary.csv
<prefix>_judge_reasoning.md
```

### فیلدهای الزامی prediction

برای SQL-positive:

```text
id
question
source_kind
difficulty
category
expected_action
actual_action
normalized_question
intent
intent_confidence
safety_label
qir
linked_schema
value_links
retrieved_examples
retrieval_diagnostics
prompt_id یا trace_id
generated_sql
gold_sql
valid_sql
execution_correct
result_hash
gold_result_hash
validation_issues
execution_error
retry_count
attempts
generation_source
latency_ms
error
```

برای behavioral:

```text
id
evaluation_type
user_utterance_fa/question
expected_action
actual_action
should_generate_sql
action_correct
abstained
safety_label
needs_clarification
final_answer
error
```

### کارهای اجرایی

1. یک test contract اضافه یا کامل کن:

```text
tests/tier1_unit/test_benchmark_artifact_contract.py
```

2. بررسی کن `export_benchmark_csvs` و `artifact_paths` یکسان فایل تولید کنند.
3. `trace_level=compact` نباید فیلدهای ضروری metric را حذف کند.
4. partial artifacts باید در crashهای طولانی قابل استفاده باشند اما final artifacts باید بدون `partial_` ساخته شوند.

### معیار پذیرش

```powershell
.\.venv\Scripts\python.exe -m pytest tests\tier1_unit\test_benchmark_artifact_contract.py tests\tier1_unit\test_graph_attempt_trace.py -q
.\.venv\Scripts\python.exe scripts\run_benchmark.py --mode gold --dataset dev --samples-per-level 1 --ablation-id artifact_contract_gold_smoke
```

قبولی یعنی:

- همه فایل‌های بالا ساخته شوند.
- `summary.json` به همه artifact paths اشاره کند.
- `paper_tables.md` خالی نباشد.
- `predictions.jsonl` و `attempts.jsonl` قابل parse باشند.

---

## P4. NLU, Schema Linking, Value Linking Metrics

### هدف

Contribution مقاله فقط end-to-end SQL نیست. باید نشان بدهی Persian normalization، schema linking و value linking قابل سنجش هستند.

### فایل‌های درگیر

```text
src/evaluation/metrics.py
src/evaluation/retrieval_metrics.py
src/schema/schema_linker.py
src/schema/value_linker.py
scripts/run_benchmark.py
tests/tier1_unit/test_schema_linker.py
tests/tier1_unit/test_value_linker_disorder_columns.py
```

### dataset metadata مورد نیاز

برای سنجش linking، هر case تا حد ممکن باید این فیلدها را داشته باشد:

```text
expected_tables
expected_columns
expected_values
expected_join_paths
expected_result_shape
```

اگر همه 400 مورد metadata ندارند، برای مقاله subset بساز:

```text
data/questions/audit/linking_eval_100.json
```

### metricهای schema linking

اضافه کن:

```text
table_recall
table_precision
column_recall
column_precision
join_path_accuracy
missing_required_element_rate
redundant_element_rate
hallucinated_schema_item_rate
schema_confidence_calibration_bins
```

### metricهای value linking

اضافه کن:

```text
value_link_accuracy
value_link_precision
value_link_recall
value_link_missing_rate
value_link_wrong_column_rate
value_link_wrong_value_rate
```

### command پیشنهادی

اگر mode جدا نداری، یک mode `retrieval` یا script analysis روی predictions بساز. پیشنهاد:

```powershell
.\.venv\Scripts\python.exe scripts\run_benchmark.py --mode retrieval --dataset positive400 --sample 0 --top-k 5 --exclude-self --ablation-id retrieval_linking_full400
.\.venv\Scripts\python.exe scripts\analyze_benchmark_artifact.py <artifact_dir> --output-dir results\error_analysis\retrieval_linking_full400
```

یا یک script مشخص:

```text
scripts/evaluate_linking.py
```

که فقط NLU/schema/value linking را اجرا کند و بدون LLM metric بدهد.

### معیار پذیرش

- یک CSV مستقل ساخته شود:

```text
schema_value_linking_metrics.csv
```

- حداقل 100 case دارای expected table/column/value برای linking evaluation باشند.
- خطاهای linking به taxonomy وصل شوند:
  - `SCHEMA_LINKING_ERROR`
  - `VALUE_LINKING_ERROR`
  - `JOIN_ERROR`
  - `MISSING_REQUIRED_SCHEMA_ELEMENT`
  - `REDUNDANT_SCHEMA_CONTEXT`

---

## P5. Retrieval/CAG Ablation

### هدف

برای مقاله باید مشخص شود CAG سبک واقعاً کمک می‌کند یا فقط prompt را شلوغ می‌کند.

### ablationهای retrieval

```text
R0: BM25 lexical only
R1: vector only
R2: hybrid BM25 + vector
R3: hybrid + reranker
R4: hybrid + schema evidence guard
```

### فایل‌های درگیر

```text
src/retrieval/hybrid_retriever.py
src/retrieval/retrieval_scorer.py
src/retrieval/context_builder.py
src/retrieval/retrieval_metrics.py
scripts/build_rag_index.py
scripts/run_benchmark.py
experiments/configs/R*.yaml
```

### context packing policy

در prompt نهایی برای local LLM:

```text
max_schema_tables = 5
max_columns_per_table = 12
max_golden_examples = 3
max_sql_skeletons = 2
max_business_rules = 10
max_prompt_chars یا max_tokens باید ثبت شود
```

### commandهای پیشنهادی

```powershell
.\.venv\Scripts\python.exe scripts\build_rag_index.py

.\.venv\Scripts\python.exe scripts\run_benchmark.py --mode retrieval --dataset dev --sample 0 --retrieval-backend bm25 --top-k 5 --exclude-self --ablation-id R0_bm25_dev

.\.venv\Scripts\python.exe scripts\run_benchmark.py --mode retrieval --dataset dev --sample 0 --retrieval-backend vector --top-k 5 --exclude-self --ablation-id R1_vector_dev

.\.venv\Scripts\python.exe scripts\run_benchmark.py --mode retrieval --dataset dev --sample 0 --retrieval-backend hybrid --top-k 5 --exclude-self --ablation-id R2_hybrid_dev

.\.venv\Scripts\python.exe scripts\run_benchmark.py --mode retrieval --dataset dev --sample 0 --retrieval-backend hybrid --reranker identity --top-k 5 --exclude-self --ablation-id R3_hybrid_identity_dev
```

### metricها

```text
retrieval_hit_rate
schema_recall_at_k
column_recall_at_k
intent_match_at_k
skeleton_match_at_k
self_overlap_removed
selected_context_tokens/chars
prompt_overflow_rate
```

### معیار پذیرش

- R0-R3 روی همان case set اجرا شوند.
- `selected_cases_hash` یکسان باشد.
- self-overlap حذف شده باشد.
- اگر reranker واقعی فعال نیست، R3 را فقط wiring baseline بنام، نه reranker quality claim.

---

## P6. Local Generation and Model Reproducibility

### هدف

مقاله باید ثابت کند هسته سیستم local/private است. پس مدل، path، quantization، context window و سرعت باید reproducible باشند.

### فایل‌های درگیر

```text
download_and_repair_hf_models_for_vtd_v1_0_4.py
models/MODEL_REGISTRY.md
models/download_repair_manifest.json
src/generation/local_llm.py
src/config/settings.py
scripts/run_agent.py
scripts/run_benchmark.py
```

### مدل‌های پیشنهادی مقاله

Main local model:

```text
Qwen2.5-Coder-7B-Instruct-GGUF Q4_K_M
```

Fast smoke model:

```text
Qwen2.5-Coder-3B-Instruct-GGUF Q4_K_M
```

Optional lightweight comparison:

```text
Qwen3-4B-Instruct-2507-GGUF
```

Optional SQL-specialized baseline:

```text
SQLCoder-7B-GGUF
```

### setup command

```powershell
cd D:\Project\ADHD-VTD
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

.\.venv\Scripts\python.exe download_and_repair_hf_models_for_vtd_v1_0_4.py --models-root .\models --only baseline --verify-only
```

اگر model missing است، download نیاز به network دارد و باید با اجازه اجرا شود:

```powershell
.\.venv\Scripts\python.exe download_and_repair_hf_models_for_vtd_v1_0_4.py --models-root .\models --only baseline --strict
```

### smoke test

```powershell
$env:VTD_DEFAULT_MODEL_PATH = "D:\Project\ADHD-VTD\models\generation\Qwen__Qwen2.5-Coder-3B-Instruct-GGUF\<model>.gguf"
$env:VTD_LLM_N_CTX = "4096"

.\.venv\Scripts\python.exe scripts\run_agent.py "درصد دانشجویانی که افسردگی دارند چقدر است؟" --verbose
```

### معیار پذیرش

- model path واقعی در `config.json` هر benchmark ثبت شود.
- `generation_latency_ms` در attempts ثبت شود.
- `model_integrity_report.json` یا manifest سلامت مدل موجود باشد.
- اگر مدل load نشد، benchmark نباید fake metric بسازد؛ باید controlled failure artifact داشته باشد.

---

## P7. Reliability and Behavioral Evaluation

### هدف

مقاله باید نشان دهد سیستم فقط SQL نمی‌سازد؛ می‌تواند `ask_clarification`, `refuse_unsafe_sql`, `refuse_schema_gap`, `answer_without_sql`, یا `controlled_failure` بدهد.

### فایل‌های درگیر

```text
src/evaluation/reliability_gate.py
src/evaluation/reliability_metrics.py
src/evaluation/reliability_gate_analysis.py
src/evaluation/sql_consistency_critic.py
src/graph/nodes/compute_reliability_node.py
src/graph/routes.py
scripts/analyze_reliability_gate_artifact.py
data/questions/special/behavior_dev.json
data/questions/special/behavior_test.json
```

### expected actions استاندارد

همه behavioral examples باید به یکی از این actionها normalize شوند:

```text
generate_sql
generate_sql_with_caveat
ask_clarification
refuse_unsafe_sql
refuse_schema_gap
answer_without_sql
answer_chart_recommendation
controlled_failure
```

اگر dataset فعلی از labelهایی مثل `safety_refusal` یا `ambiguity_clarification` استفاده می‌کند، mapping را در یک helper مرکزی قرار بده:

```text
src/evaluation/action_normalizer.py
```

### reliability modes

برای paper حداقل این‌ها را جدا کن:

```text
RG0: no reliability gate
RG1: annotation-only reliability gate
RG2: routed reliability gate, ask/refuse/fail allowed
RG3: routed gate + judge labels on subset only
```

### commandهای پیشنهادی

```powershell
.\.venv\Scripts\python.exe scripts\run_benchmark.py --mode agent --dataset behavior_dev --sample 0 --top-k 5 --exclude-self --trace-level compact --ablation-id behavior_dev_full

.\.venv\Scripts\python.exe scripts\run_benchmark.py --mode agent --dataset behavior_test --sample 0 --top-k 5 --exclude-self --trace-level compact --ablation-id behavior_test_full
```

برای annotation-only gate:

```powershell
.\.venv\Scripts\python.exe scripts\run_benchmark.py --mode agent --dataset behavior_test --sample 0 --top-k 5 --exclude-self --trace-level compact --config experiments\configs\A7_reliability_gate_smoke.yaml
```

### metricهای behavioral

```text
behavioral_expected_action_accuracy
unsafe_rejection_rate
clarification_accuracy
out_of_schema_refusal_rate
answer_without_sql_accuracy
false_abstention_rate
unsafe_pass_through_count
abstention_precision
abstention_recall
```

### معیار پذیرش

- `unsafe_pass_through_count = 0`
- behavioral metrics در `behavioral_metrics.csv` جدا از SQL-positive metrics باشند.
- اگر routed gate هنوز quality را خراب می‌کند، آن را main pipeline نکن؛ annotation-only را برای analysis گزارش کن و limitation بنویس.

---

## P8. Ablation Matrix A0-A7/A8

### هدف

برای مقاله باید نشان بدهی هر component چه اثری دارد. ablation باید artifact-backed باشد، نه جدول دستی.

### ماتریس پیشنهادی

```text
A0  Gold executor sanity check
A1  Local LLM + compact full schema, no Persian NLU, no CAG
A2  A1 + Persian normalization / intent routing
A3  A2 + schema linking
A4  A3 + value linking
A5  A4 + CAG examples/skeleton retrieval
A6  A5 + validation/read-only execution/shape checks
A7  A6 + repair/reflexion
A8  A7 + reliability gate / abstention annotation
```

با توجه به کد فعلی، configهای موجود نام‌های متفاوت دارند:

```text
experiments/configs/A0_direct_schema_only.yaml
experiments/configs/A1_persian_nlu.yaml
experiments/configs/A2_schema_linking.yaml
experiments/configs/A3_value_linking.yaml
experiments/configs/A4_cag_examples.yaml
experiments/configs/A7_full_phase10_system.yaml
```

### کارهای اجرایی

1. configهای A0-A8 را به یک naming policy واحد برسان.
2. در هر config فقط یک تغییر نسبت به قبلی فعال شود.
3. `ablation_runtime_contract` باید بگوید کدام flag واقعاً runtime-enforced است.
4. اگر flagی metadata-only یا unknown است، مقاله نباید آن را component ablation claim کند.

### command dry-run

```powershell
.\.venv\Scripts\python.exe scripts\run_ablation.py --config-dir experiments\configs --output-dir results\ablation\paper1_dry_run
```

### command execute

اول smoke:

```powershell
.\.venv\Scripts\python.exe scripts\run_ablation.py --config-dir experiments\configs --output-dir results\ablation\paper1_smoke --execute
```

بعد final روی dev یا positive400:

```powershell
.\.venv\Scripts\python.exe scripts\run_ablation.py --config-dir experiments\configs --output-dir results\ablation\paper1_positive400 --execute
```

### معیار پذیرش

- manifest همه jobs را `completed` نشان بدهد.
- همه jobs روی یک `selected_cases_hash` مشترک اجرا شده باشند.
- `deterministic_templates=false` برای main ablationها باشد.
- `safety` و `validation` اگر locked هستند، در report واضح ذکر شوند.
- ablation comparison شامل:
  - EX
  - valid SQL
  - hallucinated schema rate
  - abstention precision/recall
  - latency
  - regression count نسبت به baseline

---

## P9. Semantic/Business Judge Full Audit

### هدف

Execution accuracy کافی نیست. روی subset باید بررسی شود SQL از نظر مفهوم فارسی و business logic درست است یا نه.

### فایل‌های درگیر

```text
src/evaluation/llm_judge.py
src/evaluation/judge_consensus.py
src/evaluation/judge_agreement.py
scripts/judge_benchmark_artifact.py
scripts/analyze_judge_consensus.py
scripts/analyze_judge_agreement.py
```

### subset پیشنهادی

```text
50 failure cases
50 success cases
20 behavioral abstention cases
```

اگر هزینه مهم است، با `mock` شروع کن و برای paper فقط روی subset کوچک provider واقعی بزن.

### rubric

هر judgment باید جدا امتیاز بدهد:

```text
semantic_business_correct: yes/no/partial
metric_correct: 0/1
filter_correct: 0/1
join_logic_correct: 0/1
aggregation_correct: 0/1
result_shape_correct: 0/1
explanation_consistent: 0/1
clinical_safety_issue: 0/1
```

### command mock

```powershell
.\.venv\Scripts\python.exe scripts\judge_benchmark_artifact.py `
  <artifact_dir> `
  --judge-provider mock `
  --judge-policy semantic `
  --judge-sample-size 50 `
  --all-predictions
```

### command provider واقعی

فقط روی داده de-identified/synthetic:

```powershell
$env:OPENROUTER_API_KEY = "<key>"
.\.venv\Scripts\python.exe scripts\judge_benchmark_artifact.py `
  <artifact_dir> `
  --judge-provider openrouter `
  --judge-model <model> `
  --judge-policy semantic `
  --judge-sample-size 50 `
  --all-predictions
```

### معیار پذیرش

- judge artifacts جدا از benchmark اصلی تولید شود.
- provider errors به عنوان incorrect model output حساب نشوند.
- semantic/business correctness جایگزین EX نشود؛ فقط complementary metric باشد.
- subset selection policy در report نوشته شود.

---

## P10. Error Analysis and Paper Tables

### هدف

از artifactهای benchmark باید جدول‌های مقاله، taxonomy خطا و representative examples ساخته شود.

### فایل‌های درگیر

```text
src/evaluation/error_analyzer.py
src/evaluation/artifact_analysis.py
src/evaluation/export_utils.py
src/evaluation/statistical_tests.py
scripts/analyze_benchmark_artifact.py
scripts/analyze_ablation_manifest.py
```

### جدول‌های مقاله

حداقل این جدول‌ها لازم است:

1. Dataset summary:

```text
positive SQL examples
behavioral examples
difficulty distribution
category distribution
audit status
```

2. Main performance:

```text
EX@1 / EX@final
valid_sql_rate
result_mismatch_rate
hallucinated_table_rate
hallucinated_column_rate
latency mean/median/p95
```

3. Modular metrics:

```text
schema table/column recall
value linking accuracy
retrieval recall@k
behavioral expected action accuracy
abstention precision/recall
unsafe rejection
```

4. Ablation:

```text
A0-A8
enabled modules
EX
valid SQL
reliability
latency
delta vs previous
```

5. Robustness:

```text
standard Persian
colloquial
typo
Finglish
Jalali date
mixed Persian-English
```

6. Error taxonomy:

```text
INTENT_ERROR
PERSIAN_NORMALIZATION_ERROR
SCHEMA_LINKING_ERROR
VALUE_LINKING_ERROR
RETRIEVAL_ERROR
OUTPUT_PARSE_ERROR
SQL_SYNTAX_ERROR
UNKNOWN_TABLE
UNKNOWN_COLUMN
INVALID_JOIN_PATH
WRONG_AGGREGATION
WRONG_FILTER
RESULT_MISMATCH
CLARIFICATION_FAILURE
SAFETY_FAILURE
```

### commandها

```powershell
.\.venv\Scripts\python.exe scripts\analyze_benchmark_artifact.py <final_agent_artifact> --output-dir results\error_analysis\paper1_final

.\.venv\Scripts\python.exe scripts\analyze_ablation_manifest.py results\ablation\paper1_positive400\ablation_manifest.json --output-dir results\ablation\paper1_positive400
```

### معیار پذیرش

- `paper_tables.md` از artifact واقعی تولید شود.
- هیچ عددی دستی وارد report نشود مگر با label `manual_note`.
- paired statistical tests فقط وقتی اجرا شوند که case set مشترک است.
- اگر sample کوچک است، report باید warning بدهد.

---

## P11. Reproducibility Package and Closeout

### هدف

کسی که مقاله را می‌خواند یا داور است باید بتواند pipeline را بازتولید کند.

### فایل‌های پیشنهادی

```text
docs/PARS_SQL_PAPER1_REPRODUCIBILITY.md
docs/PARS_SQL_PAPER1_RESULTS_SUMMARY.md
results/reports/paper_tables.md
results/reports/final_artifact_manifest.json
```

### محتوای reproducibility

باید شامل این‌ها باشد:

```text
OS and Python version
dependency install command
database path and schema snapshot hash
dataset paths and hashes
model path and model integrity manifest
environment variables
exact commands for:
  gold benchmark
  retrieval ablation
  agent ablation
  behavior benchmark
  judge subset
  error analysis
expected artifact paths
known limitations
```

### commandهای final پیشنهادی

Gold sanity:

```powershell
.\.venv\Scripts\python.exe scripts\run_benchmark.py --mode gold --dataset positive400 --sample 0 --bootstrap-iterations 1000 --trace-level compact --ablation-id paper1_gold_positive400
```

Retrieval final:

```powershell
.\.venv\Scripts\python.exe scripts\run_benchmark.py --mode retrieval --dataset positive400 --sample 0 --retrieval-backend hybrid --top-k 5 --exclude-self --bootstrap-iterations 1000 --trace-level compact --ablation-id paper1_retrieval_hybrid_positive400
```

Agent main:

```powershell
.\.venv\Scripts\python.exe scripts\run_benchmark.py --mode agent --dataset positive400 --sample 0 --top-k 5 --exclude-self --bootstrap-iterations 1000 --trace-level compact --ablation-id paper1_main_local_no_templates
```

Behavior:

```powershell
.\.venv\Scripts\python.exe scripts\run_benchmark.py --mode agent --dataset behavior_test --sample 0 --top-k 5 --exclude-self --bootstrap-iterations 1000 --trace-level compact --ablation-id paper1_behavior_test
```

Judge subset:

```powershell
.\.venv\Scripts\python.exe scripts\judge_benchmark_artifact.py `
  <paper1_main_artifact> `
  --judge-provider mock `
  --judge-policy semantic `
  --judge-sample-size 100 `
  --all-predictions
```

### معیار پذیرش نهایی

- همه final artifactها در `final_artifact_manifest.json` ثبت شوند.
- README reproducibility با commandهای دقیق کامل باشد.
- `unsafe_sql=0`.
- `gold` benchmark برای gold SQLها پاس شود.
- behavioral metrics جدا از SQL metrics باشند.
- `deterministic_templates=false` در main config ثبت شده باشد.
- limitationها شفاف نوشته شوند:
  - Persian benchmark کوچک/دامنه‌محور است.
  - clinical diagnosis نیست.
  - local small LLM محدودیت دارد.
  - test split فعلی ممکن است به دلیل debug usage برای anti-overfit نهایی کافی نباشد مگر holdout جدید ساخته شود.

---

## 5. Test Strategy

### Tier 1: unit tests

سریع و deterministic:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\tier1_unit -q
```

حداقل focus suite قبل از benchmark:

```powershell
.\.venv\Scripts\python.exe -m pytest `
  tests\tier1_unit\test_intent_classifier.py `
  tests\tier1_unit\test_safety_detector.py `
  tests\tier1_unit\test_schema_linker.py `
  tests\tier1_unit\test_value_linker_disorder_columns.py `
  tests\tier1_unit\test_retrieval.py `
  tests\tier1_unit\test_prompt_builder.py `
  tests\tier1_unit\test_graph_attempt_trace.py `
  tests\tier1_unit\test_graph_routes.py `
  tests\tier1_unit\test_reliability_gate.py `
  tests\tier1_unit\test_shape_validator.py `
  tests\tier1_unit\test_aggregation_validator.py -q
```

### Tier 2: integration tests

اگر `tests/tier2_integration` وجود دارد:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\tier2_integration -q
```

اگر وجود ندارد، حداقل این integration tests را اضافه کن:

```text
test_agent_benchmark_trace.py
test_gold_benchmark_artifacts.py
test_behavior_benchmark_actions.py
test_retrieval_ablation_contract.py
```

### Tier 3: long benchmark tests

این‌ها کند هستند و نباید در unit suite باشند:

```text
positive400 full agent
behavior100 full agent
R0-R3 retrieval full
A0-A8 ablation full
judge subset
```

---

## 6. معیارهای عددی پیشنهادی برای مقاله

این اعداد target هستند، نه شرط چاپ قطعی. اگر به آن‌ها نرسیدی، همچنان می‌توانی مقاله reliability-first را با limitation درست بنویسی.

```text
Gold SQL execution success: 100%
Unsafe SQL generated: 0
Valid SQL rate: >= 90%
Main local EX on positive400: هرچه artifact-backed است، بدون template overfit
Behavioral expected action accuracy: >= 80%
Unsafe rejection rate: 100%
Abstention precision: >= 80%
Abstention recall: >= 70%
Schema table recall on linking subset: >= 85%
Column recall on linking subset: >= 75%
Value linking accuracy on value subset: >= 80%
p95 latency: گزارش شود؛ اگر بالاست limitation باشد
```

اگر `EX` پایین‌تر از انتظار است، claim مقاله را این‌طور نگه دار:

```text
PARS-SQL یک framework قابل سنجش و reliability-first برای Persian local Text-to-SQL است؛
هدف آن SOTA leaderboard جهانی نیست، بلکه benchmark، modular evaluation، safety و abstention در دامنه فارسی/سلامت روان است.
```

---

## 7. Anti-Overfit and Claim Policy

### چیزهایی که claim اصلی نیستند

- نتیجه روی `failed154`.
- نتیجه template pack که از previous failures ساخته شده.
- نتیجه‌ای که `deterministic_templates=true` دارد، مگر به عنوان ablation.
- نتیجه‌ای که `--exclude-self` ندارد.
- نتیجه‌ای که روی `test/` آلوده به debug استفاده شده و holdout جدید ندارد.
- judge result بدون artifact/cost/error report.

### claimهای مجاز

اگر artifactها آماده باشند، این claimها قابل دفاع‌اند:

```text
1. سیستم local/private و read-only است.
2. Persian normalization، schema/value linking و CAG در pipeline modular وجود دارند.
3. benchmark فارسی دامنه‌محور شامل SQL-positive و behavioral examples ساخته شده است.
4. ارزیابی فقط EX نیست؛ validation, safety, abstention, behavioral action و latency هم گزارش شده‌اند.
5. سیستم می‌تواند unsafe/ambiguous/out-of-schema را جدا مدیریت کند.
6. همه claimها با benchmark artifacts قابل بازتولید هستند.
```

---

## 8. ترتیب اجرایی کوتاه برای انجام کار

اگر فقط می‌خواهی بدانی از فردا دقیقاً چه کار کنی، این ترتیب را اجرا کن:

1. `P2` bugfixها را انجام بده، مخصوصاً `answer_without_sql`, parse failure, schema linking state.
2. `tests/tier1_unit -q` را سبز کن.
3. `gold positive400` را اجرا کن و gold SQL را 100% validate کن.
4. `retrieval R0-R3` را روی dev و بعد positive400 اجرا کن.
5. `agent positive400` را با `experiments/configs/paper1_main_local_no_templates_bounded.yaml` اجرا کن تا `deterministic_templates=false`, `--exclude-self`, `trace-level compact`, و `max_retries=1` همه در artifact ثبت شوند.
6. `behavior_test` را جدا اجرا کن.
7. artifact analysis و ablation comparison را بساز.
8. judge subset را فقط روی artifact نهایی اجرا کن.
9. `paper_tables.md`, `results_summary.md`, `reproducibility.md` را تولید کن.
10. اگر `test/` تمیز نیست، holdout/paraphrase مستقل بساز و حداقل یک validation run روی آن انجام بده.

---

## 9. Definition of Done برای مقاله اول

مقاله اول آماده نوشتن است وقتی. وضعیت فعلی هر مورد در 2026-06-22 کنار آن آمده است:

- [x] `DATASET_CARD.md` نهایی شده.  
  وضعیت: `docs/DATASET_CARD.md` ساخته شد.
- [x] همه gold SQLهای `positive400` اجرا و validate شده‌اند.  
  وضعیت: artifact `20260621_064906_gold_positive400...`, نتیجه `400/400`.
- [x] behavioral100 جدا ارزیابی شده.  
  وضعیت: `behavior_test=60` و `behavior_dev=40` کامل‌اند. مجموع: `expected_action_accuracy=76/100=0.76`, `safety_rejection_accuracy=16/16=1.0`, `clarification_accuracy=22/25=0.88`, `abstention_precision=80/90=0.8889`, `abstention_recall=80/83=0.9639`, `unsafe_sql=0`.
- [x] main agent run با مدل local و `deterministic_templates=false` انجام شده.  
  وضعیت: full `positive400` کامل است. Artifact: `results/benchmark/20260621_122748_paper1_main_local_no_templates_bounded`, نتیجه: `execution_accuracy=102/394=0.2589`, `valid_sql_rate=295/394=0.7487`, `trace_contract.validated=true`.
- [x] retrieval ablation حداقل R0-R2 انجام شده.  
  وضعیت: R0-R3 روی full dev انجام شده؛ R3 فقط identity-reranker wiring است.
- [x] ablation A0-A4/A7 artifact-backed انجام شده.  
  وضعیت: A0-A4/A7 روی 8-case smoke، full-dev bounded و full positive400 اجرا و تحلیل شد. گزارش اصلی full positive400: `results/ablation/paper1_A0_A4_A7_positive400_split/merged/ablation_comparison.md`. محدودیت: A5/A6 جداگانه در این matrix نیامده‌اند.
- [x] reliability/abstention metrics جدا گزارش شده.  
  وضعیت: روی `behavior_test` کامل است؛ `abstention_recall=1.0`, `unsafe_sql=0`.
- [x] error taxonomy و representative failures ساخته شده.  
  وضعیت: گزارش main ساخته شد: `results/error_analysis/paper1_main_local_bounded/error_report.md`, summary: `results/error_analysis/paper1_main_local_bounded/analysis_summary.json`.
- [x] semantic judge full audit، اگر استفاده می‌شود، artifact-backed است.  
  وضعیت: OpenRouter full 400-case authoritative audit کامل است. Artifact: `results/judgments/paper1_main_semantic_openrouter_s400_split/merged_authoritative`, نتیجه: `business_correct=161/400=0.4025`, `business_incorrect=239/400=0.5975`, `authoritative=true`, `provider_error=0`, `provider_parse_error=0`.
- [x] `paper_tables.md` از artifactها تولید شده.  
  وضعیت: combined table pack ساخته شد: `results/reports/paper_tables.md`.
- [x] `final_artifact_manifest.json` همه مسیرهای artifact اصلی را ثبت کرده.  
  وضعیت: ساخته شد: `results/reports/final_artifact_manifest.json`. optional extensionها جدا از package فعلی علامت خورده‌اند.
- [x] هیچ عددی از debug/overfit run به عنوان main result گزارش نشده.  
  وضعیت: در این سند و summary docs صریح شده است.
- [x] limitationهای clinical/non-diagnostic/privacy/local model صریح نوشته شده‌اند.  
  وضعیت: `docs/DATASET_CARD.md` و `docs/paper/limitations.md`.

---

## 10. ساختار پیشنهادی مقاله

وقتی برنامه بالا انجام شد، مقاله را با این ساختار بنویس:

```text
1. Introduction
   - Persian Text-to-SQL gap
   - privacy-sensitive mental-health/student-lifestyle analytics
   - reliability-first goal

2. Related Work
   - general Text-to-SQL systems
   - reliable healthcare Text-to-SQL
   - schema/value linking
   - multilingual/Persian evaluation gap
   - benchmark annotation validity

3. VTD-500 Benchmark
   - 400 SQL-positive
   - 100 behavioral
   - audit protocol
   - split and leakage policy
   - dataset card and limitations

4. PARS-SQL Method
   - Persian NLU
   - QIR
   - schema/value linking
   - compact CAG
   - local LLM generation
   - validation/repair
   - reliability gate and abstention

5. Evaluation Protocol
   - EX and valid SQL
   - linking metrics
   - retrieval metrics
   - behavioral expected-action metrics
   - reliability and safety
   - latency
   - semantic judge subset

6. Results
   - main local model
   - ablations
   - behavioral evaluation
   - robustness
   - error analysis

7. Discussion
   - why Persian/local is hard
   - where system fails
   - privacy/safety tradeoffs
   - why not BIRD/Spider leaderboard claim

8. Ethics and Limitations
   - non-diagnostic
   - de-identified/synthetic policy
   - local data privacy
   - benchmark scope

9. Conclusion
```

---

## 11. فایل‌هایی که احتمالاً باید در ادامه ویرایش شوند

این لیست برای اجرای برنامه است:

```text
src/graph/routes.py
src/graph/workflow.py
src/graph/state.py
src/graph/nodes/base_nodes.py
src/generation/output_parser.py
src/schema/value_linker.py
src/evaluation/metrics.py
src/evaluation/export_utils.py
src/evaluation/error_analyzer.py
scripts/run_benchmark.py
scripts/run_ablation.py
scripts/analyze_benchmark_artifact.py
experiments/configs/*.yaml
docs/DATASET_CARD_DRAFT.md
docs/BENCHMARK_AND_TEST_GUIDE.md
docs/phases/PHASE_18_7_ZERO_SHOT_MASTERY.md
```

تست‌هایی که احتمالاً باید اضافه یا تکمیل شوند:

```text
tests/tier1_unit/test_benchmark_artifact_contract.py
tests/tier1_unit/test_output_parser.py
tests/tier1_unit/test_graph_routes.py
tests/tier1_unit/test_behavioral_action_metrics.py
tests/tier1_unit/test_schema_value_linking_metrics.py
tests/tier1_unit/test_reranker_cli_contract.py
tests/tier1_unit/test_dataset_card_contract.py
```

---

## 12. یادداشت نهایی برای اجراکننده

این پروژه الان بیشتر از آنکه به feature جدید نیاز داشته باشد، به evidence discipline نیاز دارد. یعنی هر تغییر باید این مسیر را طی کند:

```text
code change
-> focused unit tests
-> smoke benchmark
-> full artifact-backed benchmark
-> error analysis
-> ablation comparison
-> paper table
```

اگر تغییری فقط روی یک failure subset نتیجه عالی می‌دهد ولی روی full400 یا holdout regression می‌آورد، آن تغییر را به عنوان debug/ablation نگه دار و وارد main pipeline مقاله نکن.

برای مقاله اول، بهترین خروجی یک سیستم کاملاً قابل سنجش و قابل دفاع است، حتی اگر `EX` آن از leaderboardهای انگلیسی پایین‌تر باشد. novelty اصلی این پروژه ترکیب Persian benchmark، local/private execution، schema/value linking، deterministic validation، behavioral abstention و modular evaluation است.

---

## 13. ادغام نهایی با `task.md` و برنامه دانلودی

این بخش دقیقاً مشخص می‌کند هر موردی که در `paper1_implementation_plan.md` آمده، در repo فعلی چه وضعیتی دارد و برای مقاله اول چه کاری باید انجام شود.

| موضوع در برنامه دانلودی | وضعیت فعلی در repo | اقدام لازم برای مقاله اول |
|---|---|---|
| `scripts/audit_phase0_50q.py` | نسخه‌های legacy در `archive/scripts_legacy/` وجود دارند؛ artifactهای Phase 0 در `data/questions/audit/` موجود است. | اسکریپت modern لازم نیست از صفر نوشته شود مگر برای بازتولید. به جای آن، `scripts/validate_dataset_sql.py` و `src/evaluation/phase0_audit.py` را به عنوان مسیر رسمی مستند کن و یک rerun gold روی `positive400` بزن. |
| `PositiveExample` و `BehavioralExample` | `src/evaluation/dataset_loader.py` loader عمومی `LoadedDataset` و `normalize_case` دارد، ولی typeهای صریح Pydantic برای positive/behavioral ندارد. | `src/core/dataset_types.py` یا `src/evaluation/dataset_contracts.py` اضافه کن و loader را به validation اختیاری مجهز کن. |
| `src/core/trace.py` | trace در `src/graph/state.py` با `SQLAttempt`, `VTDState`, prediction records داخل `scripts/run_benchmark.py` پراکنده است. | یا `src/core/trace.py` را به عنوان contract مرکزی اضافه کن، یا یک سند/adapter بساز که state فعلی را به `AttemptTrace` و `PredictionRecord` تبدیل کند. برای مقاله، contract مرکزی بهتر است. |
| DATA_AWARE_SIGNALS در ambiguity detector | در Phase 18 و `IntentClassifier`/`AmbiguityDetector` بخشی از این منطق اضافه شده است. | تست‌های explicit برای «تحلیل کن + دیتاست/جدول/آمار» اضافه کن تا SQL-positiveهای vague اشتباهاً abstain نشوند. |
| privacy/individual-level unsafe detection | safety validator و detector وجود دارند، اما باید individual-level privacy policy جدا تست شود. | الگوی «شماره دانشجویی/نام/فرد خاص/raw row sensitive» را به `SafetyIntentDetector` و behavioral set اضافه کن. |
| `QueryIR` | `src/core/query_ir.py` وجود دارد و Phase 18.7e آن را تقویت کرده است. | QIR باید در artifact نهایی همیشه ثبت شود و metrics/dimensions/filter خالی برای grouped/rate questions failure محسوب شود. |
| `SchemaLinker v2` | `src/schema/schema_linker.py` با alias، glossary، metric definitions، hard-gating و evidence وجود دارد. | confidence/evidence/unresolved/join_hints باید کامل به benchmark prediction برسند و linking metrics مستقل ساخته شوند. |
| `generate_value_aliases.py` و `value_aliases.fa.json` | `value_dictionary.generated.json` و `ValueLinker.MANUAL_ALIASES` وجود دارد؛ فایل alias جدا وجود ندارد. | یا `scripts/generate_value_aliases.py` را بساز، یا تصمیم بگیر manual aliases + value dictionary منبع رسمی است. برای مقاله بهتر است generator و artifact alias ساخته شود. |
| Lightweight context packer | `src/retrieval/context_builder.py` فقط examples را pack می‌کند؛ schema context محدودسازی اصلی در prompt/schema_linking پراکنده است. | max tables/columns/examples/tokens را به صورت config و artifact ثبت کن؛ `ContextBuilder` یا `PromptBuilder` باید diagnostics بدهد. |
| `src/sql_validation/error_taxonomy.py` | taxonomy در `src/reflexion/error_taxonomy.py` و `src/evaluation/error_analyzer.py` پراکنده است. | یک enum رسمی در `src/sql_validation/error_taxonomy.py` یا `src/evaluation/error_taxonomy.py` بساز و همه reportها را به آن map کن. |
| `src/graph/nodes/reliability_gate.py` | node فعلی `src/graph/nodes/compute_reliability_node.py` است و gate اصلی در `src/evaluation/reliability_gate.py`. | یا یک wrapper node با نام واضح اضافه کن، یا در سند و workflow توضیح بده `compute_reliability_node` همان reliability gate graph node است. |
| `src/evaluation/paper_tables.py` | `src/evaluation/export_utils.py::generate_paper_tables` وجود دارد. | برای paper-grade tableها بهتر است `paper_tables.py` جدا بسازی و `export_utils` فقط wrapper بماند. |
| A0-A7 ablation YAMLها | configهای A0-A4 و A7 وجود دارند؛ نام‌ها با برنامه دانلودی فرق دارند. | naming را canonical کن و اگر لازم است alias config اضافه کن: `A0_raw_local_llm`, `A1_norm`, `A2_schema`, ... |

---

## 14. Backlog اجرایی اولویت‌بندی‌شده

این backlog، نسخه عملی و status-aware برای ادامه کار است. هر item باید با تست و artifact بسته شود.

### B0. Blockerهای قبل از هر benchmark نهایی

- [x] **B0.1 Dataset contract types**
  - فایل پیشنهادی: `src/core/dataset_types.py`
  - شامل: `PositiveExample`, `BehavioralExample`, `DatasetPackageSummary`
  - اتصال: `src/evaluation/dataset_loader.py`
  - تست: `tests/tier1_unit/test_dataset_loader.py`
  - پذیرش: positive و behavioral با schema/type جدا validate شوند و behavioral وارد EX نشود.
  - انجام‌شده در شروع اجرای برنامه: `src/core/dataset_types.py` اضافه شد، loader helperها اضافه شدند، و `tests/tier1_unit/test_dataset_contracts.py` سبز شد.

- [x] **B0.2 Central trace contract**
  - فایل پیشنهادی: `src/core/trace.py`
  - شامل: `AttemptTrace`, `PredictionRecord`, `RetrievalTrace`, `ReliabilityTrace`
  - اتصال: `src/graph/state.py`, `scripts/run_benchmark.py`
  - تست: `tests/tier1_unit/test_trace_contract.py`
  - پذیرش: هر prediction و attempt با contract مرکزی قابل validate باشد.
  - انجام‌شده در ادامه اجرا: `src/evaluation/trace_adapter.py` اضافه شد، `run_benchmark.py` قبل از نوشتن partial/final artifacts رکوردهای prediction و attempt را با contract مرکزی validate می‌کند، و `summary.trace_contract` ثبت می‌شود. تست‌های `test_trace_adapter.py` و artifact contract سبز شدند.

- [x] **B0.3 Parse failure hardening**
  - فایل‌ها: `src/generation/output_parser.py`, `src/graph/nodes/base_nodes.py`
  - پذیرش: invalid JSON هرگز raw LLM response را به عنوان SQL validate نکند.
  - تست: `tests/tier1_unit/test_output_parser.py`, `tests/tier1_unit/test_graph_attempt_trace.py`
  - انجام‌شده در شروع اجرای برنامه: `parse_llm_output` روی parse failure مقدار `generated_sql=None` می‌دهد و `validate_sql` attempt شکست parse را بدون validate کردن raw response ثبت می‌کند.

- [x] **B0.4 Graph routing consistency**
  - فایل‌ها: `src/graph/routes.py`, `src/graph/workflow.py`, `src/graph/nodes/base_nodes.py`
  - مورد خاص: `route_pre_generation` نباید مسیری برگرداند که در workflow mapping نیست.
  - پذیرش: definition/chart/no-SQL/unsafe/ambiguous/sql-positive همه route تست دارند.
  - تست: `tests/tier1_unit/test_graph_routes.py`
  - انجام‌شده در شروع اجرای برنامه: مسیر `answer_without_sql` در workflow به node خروجی موجود map شد و compile تست شد.

- [x] **B0.5 Safety and privacy behavioral gate**
  - فایل‌ها: `src/nlu/safety_intent_detector.py`, `src/graph/routes.py`, `src/output/answer_formatter.py`
  - پذیرش: `unsafe_sql=0`, `unsafe_pass_through=0`, `safety_rejection_accuracy >= 0.8` روی behavior smoke.
  - command:
    ```powershell
    .\.venv\Scripts\python.exe scripts\run_benchmark.py --mode agent --dataset behavior_dev --sample 20 --ablation-id phase12_output_integration --trace-level full
    ```
  - انجام‌شده در ادامه اجرا: privacy/individual-level، hallucination/deceptive schema mapping و cherry-picking به `SafetyIntentDetector` اضافه شدند؛ `safety_label`, `ambiguity_score`, `needs_clarification`, `intent_confidence` و actionهای normalized در prediction ثبت می‌شوند.
  - smoke artifact:
    `results/benchmark/20260621_064530_agent_behavior_dev_qwen2-5-coder-7b_phase12_output_integration_b0_5`
  - نتیجه smoke روی 20 مورد `behavior_dev`: `unsafe_sql=0`, `safety_rejection_accuracy=1.0`, `abstention_precision=1.0`, `abstention_recall=1.0`, `clarification_accuracy=0.8`, `trace_contract.validated=true`.
  - تکمیل‌شده در B1.2: mismatchهای ambiguous clarification با deterministic routing و action normalization حل شدند؛ safety/privacy gate دیگر blocker نیست.

- [x] **B0.6 Reranker CLI contract**
  - فایل: `scripts/run_benchmark.py`
  - پذیرش: اگر docs command شامل `--reranker` است، parser هم باید آن را داشته باشد یا docs باید اصلاح شود.
  - تست: `tests/tier1_unit/test_reranker_cli_contract.py`
  - انجام‌شده در شروع اجرای برنامه: `--reranker` اضافه شد. مدل-backed reranker هنوز پیاده نشده و artifactها warning می‌نویسند که identity placeholder استفاده شده است.

### B1. Evidence لازم برای مقاله اول

- [x] **B1.1 Gold SQL closeout**
  - command:
    ```powershell
    .\.venv\Scripts\python.exe scripts\run_benchmark.py --mode gold --dataset positive400 --sample 0 --bootstrap-iterations 1000 --trace-level compact --ablation-id paper1_gold_positive400
    ```
  - پذیرش: همه gold SQLها validate/execute شوند یا brokenها با fix decision ثبت شوند.
  - انجام‌شده در ادامه اجرا:
    `results/benchmark/20260621_064906_gold_positive400_qwen2-5-coder-7b_paper1_gold_positive400`
  - نتیجه: `total_evaluated=400`, `execution_accuracy=1.0`, `valid_sql_rate=1.0`, `failures=0`, `unsafe_sql=0`, `trace_contract.validated=true`.
  - اصلاح artifact contract: `error_taxonomy.csv` حتی وقتی خطا صفر است به صورت header-only ساخته می‌شود.

- [x] **B1.2 Full behavioral benchmark**
  - command:
    ```powershell
    .\.venv\Scripts\python.exe scripts\run_benchmark.py --mode agent --dataset behavior_test --sample 0 --top-k 5 --exclude-self --bootstrap-iterations 1000 --trace-level compact --ablation-id paper1_behavior_test
    ```
  - پذیرش: behavior metrics جدا از SQL metrics گزارش شوند.
  - انجام‌شده در ادامه اجرا:
    - action normalization برای aliases رفتاری مثل `refuse_privacy_or_offer_aggregate`, `refuse_data_fabrication`, `answer_with_sql_optional_explanation`, `generate_sql_with_caveat` مرکزی شد.
    - `expected_action_accuracy` به metricهای summary اضافه شد تا action-policy جدا از execution/result correctness گزارش شود.
    - `exception_prediction` هم `expected_action_normalized`, `actual_action_normalized`, `action_correct`, `execution_passed`, `trace_id` و `final_answer` را ثبت می‌کند تا context overflow هم trace contract را ناقص نکند.
    - full artifact نهایی:
      `results/benchmark/20260621_072711_agent_behavior_test_qwen2-5-coder-7b_paper1_behavior_test_b1_2_actionfix`
  - نتیجه full `behavior_test` روی 60 مورد:
    - `expected_action_accuracy=52/60=0.8667` با CI95 تقریبی `[0.7833, 0.95]`
    - `safety_rejection_accuracy=10/10=1.0`
    - `clarification_accuracy=13/14=0.9286`
    - `abstention_precision=50/56=0.8929`
    - `abstention_recall=50/50=1.0`
    - `unsafe_sql=0`
    - `valid_sql_rate=6/10=0.6` روی SQL-positive behavioral cases
    - `execution_accuracy=0/10=0.0` روی SQL-positive behavioral cases؛ این شکست‌ها عمدتاً `RESULT_MISMATCH`, `INVALID_SQL`, و context overflow در typo/Finglish/cross-source هستند و باید در B1.3/B1.4 جداگانه دنبال شوند.
    - `trace_contract.validated=true` با `predictions=60`, `attempts=22`.
  - verification بعد از اصلاحات B1.2:
    ```powershell
    .\.venv\Scripts\python.exe -m pytest tests\tier1_unit -q
    ```
    نتیجه قبلی: `405 passed, 3 warnings`. نتیجه بعد از bounded retry config: `411 passed, 3 warnings`.
  - behavior_dev full بعداً اجرا شد:
    `results/benchmark/20260621_205133_agent_behavior_dev_qwen2_5-coder-7b-instruct-q4_k_m_paper1_behavior_dev_full`
  - behavior_dev نتیجه:
    `total_evaluated=40`, `expected_action_accuracy=24/40=0.6`, `safety_rejection_accuracy=6/6=1.0`, `clarification_accuracy=9/11=0.8182`, `abstention_precision=30/34=0.8824`, `abstention_recall=30/33=0.9091`, `valid_sql_rate=5/7=0.7143`, `execution_accuracy=0/7=0.0`, `unsafe_sql=0`, `trace_contract.validated=true`.
  - مجموع behavioral100:
    `expected_action_accuracy=76/100=0.76`, `safety_rejection_accuracy=16/16=1.0`, `clarification_accuracy=22/25=0.88`, `abstention_precision=80/90=0.8889`, `abstention_recall=80/83=0.9639`, `SQL-positive valid_sql_rate=11/17=0.6471`, `SQL-positive execution_accuracy=0/17=0.0`, `unsafe_sql=0`.

- [x] **B1.3 Main no-template local run**
  - command قدیمی که فقط برای reference نگه داشته شده و برای full نهایی توصیه نمی‌شود، چون `max_retries` را از settings می‌گیرد:
    ```powershell
    $env:VTD_LLM_N_CTX="8192"
    .\.venv\Scripts\python.exe scripts\run_benchmark.py --mode agent --dataset positive400 --sample 0 --top-k 5 --exclude-self --bootstrap-iterations 1000 --trace-level compact --ablation-id paper1_main_local_no_templates
    ```
  - command رسمی ادامه کار:
    ```powershell
    $env:VTD_LLM_N_CTX="8192"
    .\.venv\Scripts\python.exe scripts\run_benchmark.py --config experiments\configs\paper1_main_local_no_templates_bounded.yaml
    ```
  - پذیرش: `deterministic_templates=false` در config ثبت شود.
  - smoke preflight انجام‌شده:
    ```powershell
    $env:VTD_LLM_N_CTX="8192"
    .\.venv\Scripts\python.exe scripts\run_benchmark.py --mode agent --dataset positive400 --sample 5 --top-k 5 --exclude-self --bootstrap-iterations 200 --trace-level compact --ablation-id paper1_main_local_no_templates_smoke
    ```
  - smoke artifact:
    `results/benchmark/20260621_073923_agent_positive400_qwen2-5-coder-7b_paper1_main_local_no_templates_smoke`
  - smoke نتیجه: `execution_accuracy=3/5=0.6`, `valid_sql_rate=5/5=1.0`, `expected_action_accuracy=5/5=1.0`, `trace_contract.validated=true`.
  - smoke config تایید کرد: `module_flags.deterministic_templates=false` و `llm_context_window=8192`.
  - full attempt diagnostic انجام شد:
    ```powershell
    $env:VTD_LLM_N_CTX="8192"
    .\.venv\Scripts\python.exe scripts\run_benchmark.py --mode agent --dataset positive400 --sample 0 --top-k 5 --exclude-self --bootstrap-iterations 1000 --trace-level compact --ablation-id paper1_main_local_no_templates
    ```
  - diagnostic artifact:
    `results/benchmark/20260621_104339_agent_positive400_qwen2-5-coder-7b_paper1_main_local_no_templates`
  - diagnostic نتیجه: بعد از `9/400` متوقف شد؛ `max_retries=5` باعث repair/reflexion loopهای طولانی شد. این artifact فقط evidence برای تغییر runtime config است و paper result نیست.
  - runtime fix انجام شد:
    - `features.max_retries` در configهای YAML خوانده می‌شود.
    - مقدار override به `VTDState.max_retries` و `initialize_trace` می‌رسد.
    - summary/config artifact مقدار `max_retries` و `max_retries_source` را ثبت می‌کند.
    - `abstention` در runtime contract به‌صورت locked policy ثبت شد و warning ناشناخته ندارد.
  - bounded smoke انجام‌شده:
    ```powershell
    $env:VTD_LLM_N_CTX="8192"
    .\.venv\Scripts\python.exe scripts\run_benchmark.py --config experiments\configs\paper1_main_local_no_templates_bounded_smoke.yaml
    ```
  - bounded smoke artifact نهایی:
    `results/benchmark/20260621_112756_paper1_main_local_no_templates_bounded_smoke`
  - bounded smoke نتیجه:
    `sample=10`, `execution_accuracy=4/10=0.4`, `valid_sql_rate=10/10=1.0`, `expected_action_accuracy=7/10=0.7`, `max_retries=1`, `max_retries_source=config`, `trace_contract.validated=true`, `ablation_runtime_contract.warnings=[]`.
  - full positive400 انجام‌شده:
    `results/benchmark/20260621_122748_paper1_main_local_no_templates_bounded`
  - full نتیجه:
    `total_evaluated=400`, `execution_accuracy=102/394=0.2589`, `valid_sql_rate=295/394=0.7487`, `failures=298`, `reliability_score=-72.5`, `unsafe_sql=0`, `max_retries=1`, `max_retries_source=config`, `deterministic_templates=false`, `trace_contract.validated=true`.
  - خطاهای اصلی:
    `RESULT_MISMATCH=199`, `INVALID_SQL=93`, `MISSING_GENERATED_SQL=6`.

- [x] **B1.4 Retrieval R0-R3 final**
  - command:
    ```powershell
    .\.venv\Scripts\python.exe scripts\run_ablation.py R0_retrieval_bm25.yaml R1_retrieval_vector.yaml R2_retrieval_hybrid.yaml R3_retrieval_hybrid_rerank.yaml --output-dir results\ablation\paper1_retrieval_final --execute
    ```
  - پذیرش: same selected case hash و report artifact-backed.
  - smoke 8-case command بالا انجام شد:
    `results/ablation/paper1_retrieval_final/ablation_manifest.json`
  - full-dev command انجام‌شده برای artifact قابل گزارش‌تر:
    ```powershell
    .\.venv\Scripts\python.exe scripts\run_ablation.py experiments\configs\R0_retrieval_bm25_dev_full.yaml experiments\configs\R1_retrieval_vector_dev_full.yaml experiments\configs\R2_retrieval_hybrid_dev_full.yaml experiments\configs\R3_retrieval_hybrid_rerank_dev_full.yaml --output-dir results\ablation\paper1_retrieval_final_dev_full --execute
    ```
  - full-dev manifest:
    `results/ablation/paper1_retrieval_final_dev_full/ablation_manifest.json`
  - full-dev نتیجه:
    - هر چهار job `completed`، هر کدام `total_evaluated=60`, `failures=0`.
    - selected cases hash مشترک برای R0-R3:
      `d83596c1a3f32e1bf4e27a7db38cd7cab0c27632ca77ba0da91ee0d8a40721fa`
    - `trace_contract.validated=true` برای هر چهار artifact.
    - `retrieval_hit_rate=60/60=1.0` و `retrieval_miss_rate=0/60=0.0` در summary هر run.
    - latency mean: R0 BM25 `2.85ms`, R1 vector `83.38ms`, R2 hybrid `81.45ms`, R3 hybrid-rerank identity `77.23ms`.
    - محدودیت: R3 هنوز reranker واقعی نیست و طبق config فقط identity placeholder را verify می‌کند.

- [x] **B1.5 A0-A4/A7 paper-grade ablation**
  - شرط: اول B0 کامل شود.
  - حداقل: balanced dev با حداقل 20 case per config یا full positive400 اگر زمان/هزینه پذیرفته شد.
  - پذیرش: historical 8-case smoke به عنوان final result استفاده نشود.
  - smoke/diagnostic اجراشده:
    ```powershell
    .\.venv\Scripts\python.exe scripts\run_ablation.py `
      experiments\configs\A0_direct_schema_only.yaml `
      experiments\configs\A1_persian_nlu.yaml `
      experiments\configs\A2_schema_linking.yaml `
      experiments\configs\A3_value_linking.yaml `
      experiments\configs\A4_cag_examples.yaml `
      experiments\configs\A7_full_phase10_system.yaml `
      --output-dir results\ablation\paper1_A0_A4_A7_dev `
      --execute
    ```
  - analysis command صحیح:
    ```powershell
    .\.venv\Scripts\python.exe scripts\analyze_ablation_manifest.py `
      results\ablation\paper1_A0_A4_A7_dev\ablation_manifest.json `
      --output-dir results\ablation\paper1_A0_A4_A7_dev
    ```
  - artifact:
    `results/ablation/paper1_A0_A4_A7_dev/ablation_comparison.md`
  - نتیجه smoke:
    - `jobs_completed=6/6`, `same_selected_cases_hash=true`, `evaluated=8` برای هر config.
    - EX: A0 `0.1429`, A1 `0.1429`, A2 `0.1429`, A3 `0.1429`, A4 `0.2857`, A7 `0.4286`.
    - Valid SQL: A0 `0.5714`, A1 `0.7143`, A2 `0.5714`, A3 `0.5714`, A4 `0.5714`, A7 `0.8571`.
  - وضعیت: artifact-backed smoke است، اما هنوز برای ablation claim اصلی مقاله کافی نیست.
  - configs آماده‌شده برای اجرای بزرگ‌تر و قابل‌استنادتر روی full dev:
    ```text
    experiments/configs/A0_direct_schema_only_dev_full_bounded.yaml
    experiments/configs/A1_persian_nlu_dev_full_bounded.yaml
    experiments/configs/A2_schema_linking_dev_full_bounded.yaml
    experiments/configs/A3_value_linking_dev_full_bounded.yaml
    experiments/configs/A4_cag_examples_dev_full_bounded.yaml
    experiments/configs/A7_full_phase10_system_dev_full_bounded.yaml
    ```
  - dry-run contract برای این ablation تمیز است:
    `results/ablation/paper1_A0_A4_A7_dev_full_bounded_dryrun/ablation_manifest.json`.
  - مشخصات اجرای بعدی:
    `cases_per_config=60`, `max_retries=1`, `trace_level=compact`, `deterministic_templates=false`, `ablation_runtime_contract.warnings=[]`.
  - دستور اجرای بعدی:
    ```powershell
    .\.venv\Scripts\python.exe scripts\run_ablation.py `
      experiments\configs\A0_direct_schema_only_dev_full_bounded.yaml `
      experiments\configs\A1_persian_nlu_dev_full_bounded.yaml `
      experiments\configs\A2_schema_linking_dev_full_bounded.yaml `
      experiments\configs\A3_value_linking_dev_full_bounded.yaml `
      experiments\configs\A4_cag_examples_dev_full_bounded.yaml `
      experiments\configs\A7_full_phase10_system_dev_full_bounded.yaml `
      --output-dir results\ablation\paper1_A0_A4_A7_dev_full_bounded `
      --execute
    ```
  - دستور تحلیل بعد از پایان اجرا:
    ```powershell
    .\.venv\Scripts\python.exe scripts\analyze_ablation_manifest.py `
      results\ablation\paper1_A0_A4_A7_dev_full_bounded\ablation_manifest.json `
      --output-dir results\ablation\paper1_A0_A4_A7_dev_full_bounded
    ```
  - execution artifact:
    `results/ablation/paper1_A0_A4_A7_dev_full_bounded/ablation_manifest.json`
  - analysis artifacts:
    ```text
    results/ablation/paper1_A0_A4_A7_dev_full_bounded/ablation_comparison.md
    results/ablation/paper1_A0_A4_A7_dev_full_bounded/ablation_comparison.json
    ```
  - نتیجه full-dev bounded:
    - `jobs_completed=6/6`, `same_dataset_hash=true`, `same_selected_cases_hash=true`, `evaluated=60` برای هر config.
    - A0: `EX=4/58=0.0690`, `valid_sql=40/58=0.6897`, `reliability=-25.5`, `unsafe_sql=0`.
    - A1: `EX=4/58=0.0690`, `valid_sql=38/58=0.6552`, `reliability=-24.0`, `unsafe_sql=0`.
    - A2: `EX=4/58=0.0690`, `valid_sql=40/58=0.6897`, `reliability=-25.5`, `unsafe_sql=0`.
    - A3: `EX=4/58=0.0690`, `valid_sql=39/58=0.6724`, `reliability=-25.5`, `unsafe_sql=0`.
    - A4: `EX=15/58=0.2586`, `valid_sql=42/58=0.7241`, `reliability=-4.25`, `unsafe_sql=0`.
    - A7: `EX=17/58=0.2931`, `valid_sql=40/58=0.6897`, `reliability=1.25`, `unsafe_sql=0`.
  - interpretation:
    در full-dev، A4/CAG بیشترین جهش را نسبت به A0-A3 ایجاد می‌کند؛ A7 بهترین EX و تنها reliability مثبت را دارد، اما latency و failure count بالا می‌ماند. این نتیجه اکنون evidence توسعه‌ای است و claim اصلی ablation باید از full positive400 زیر بیاید.
  - full positive400 execution/analysis artifacts:
    ```text
    results/ablation/paper1_A0_A4_A7_positive400_split/merged/ablation_manifest.json
    results/ablation/paper1_A0_A4_A7_positive400_split/merged/ablation_comparison.md
    results/ablation/paper1_A0_A4_A7_positive400_split/merged/ablation_comparison.json
    ```
  - نتیجه full positive400:
    - `jobs_completed=6/6`, `same_dataset_hash=true`, `same_selected_cases_hash=true`, `evaluated=400` برای هر config.
    - A0: `EX=41/394=0.1041`, `valid_sql=269/394=0.6827`, `reliability=-165.25`, `unsafe_sql=0`.
    - A1: `EX=42/394=0.1066`, `valid_sql=269/394=0.6827`, `reliability=-168.25`, `unsafe_sql=0`.
    - A2: `EX=42/394=0.1066`, `valid_sql=264/394=0.6701`, `reliability=-161.50`, `unsafe_sql=0`.
    - A3: `EX=41/394=0.1041`, `valid_sql=266/394=0.6751`, `reliability=-163.00`, `unsafe_sql=0`.
    - A4: `EX=101/394=0.2563`, `valid_sql=274/394=0.6954`, `reliability=-56.50`, `unsafe_sql=0`.
    - A7: `EX=101/394=0.2563`, `valid_sql=276/394=0.7005`, `reliability=-61.25`, `unsafe_sql=0`.
  - interpretation full positive400:
    جهش اصلی با اضافه شدن CAG رخ می‌دهد: A3 `41/394` به A4 `101/394`. A7 نسبت به A4 در EX بهتر نیست، اما valid SQL را کمی بهتر می‌کند و در این run latency پایین‌تری دارد.

- [x] **B1.6 Semantic judge success+failure full audit**
  - شرط: redaction policy فعال باشد.
  - پذیرش: failure-only نباشد؛ حداقل failures + sample successes قضاوت شوند.
  - command نمونه:
    ```powershell
    .\.venv\Scripts\python.exe scripts\judge_benchmark_artifact.py `
      <artifact_dir> `
      --judge-provider mock `
      --judge-policy semantic `
      --judge-sample-size 100 `
      --all-predictions
    ```
  - OpenRouter run انجام‌شده:
    `results/judgments/paper1_main_semantic_openrouter`
  - نتیجه:
    `total_judged=50`, `provider=openrouter`, `model=qwen/qwen3.6-plus`, `failures_only=false`, `redaction_applied=true`, اما `provider_error=50/50`, `authoritative=false`, `semantic_business_counts.unjudged=50`.
  - وضعیت: artifact-backed provider failure است، نه semantic correctness result. برای claim مقاله باید judge rerun موفق یا human review subset انجام شود.
  - علت دقیق خطای provider در `judgments.jsonl`: `HTTP Error 402: Payment Required`.
  - mock sanity run موفق است، اما claim-ready نیست:
    `results/judgments/paper1_main_semantic_mock_s50`.
  - خلاصه mock:
    `total_judged=50`, `exact_sql_match=19`, `invalid_sql=2`, `requires_semantic_review=11`, `unjudged=18`, `authoritative=false`.
  - بعد از رفع اعتبار/دسترسی OpenRouter، اول probe سه‌نمونه‌ای اجرا شود:
    ```powershell
    $env:OPENROUTER_API_KEY="<key>"
    .\.venv\Scripts\python.exe scripts\judge_benchmark_artifact.py `
      results\benchmark\20260621_122748_paper1_main_local_no_templates_bounded `
      --judge-provider openrouter `
      --judge-model qwen/qwen3.6-plus `
      --judge-policy semantic `
      --case-ids VTD-001 VTD-002 VTD-003 `
      --all-predictions `
      --output-dir results\judgments\paper1_main_semantic_openrouter_s3_probe
    ```
  - probe سه‌نمونه‌ای OpenRouter موفق است:
    `results/judgments/paper1_main_semantic_openrouter_s3_probe`.
  - نتیجه probe:
    `total_judged=3`, `authoritative=true`, `authoritative_judgments=3`, `business_correct=2`, `business_incorrect=1`, `redaction_applied=true`.
  - فقط اگر probe مقدار `provider_error=0` داشت، rerun پنجاه‌نمونه‌ای انجام شود:
    ```powershell
    .\.venv\Scripts\python.exe scripts\judge_benchmark_artifact.py `
      results\benchmark\20260621_122748_paper1_main_local_no_templates_bounded `
      --judge-provider openrouter `
      --judge-model qwen/qwen3.6-plus `
      --judge-policy semantic `
      --judge-sample-size 50 `
      --all-predictions `
      --output-dir results\judgments\paper1_main_semantic_openrouter_s50_rerun
    ```
  - rerun پنجاه‌نمونه‌ای OpenRouter انجام شد و authoritative است:
    `results/judgments/paper1_main_semantic_openrouter_s50_rerun`.
  - نتیجه:
    `total_judged=50`, `authoritative=true`, `authoritative_judgments=50`, `business_correct=39/50=0.78`, `business_incorrect=11/50=0.22`, `provider_error=0`, `provider_parse_error=0`, `redaction_applied=true`.
  - تفسیر:
    این artifact اولین subset موفق بود و برای audit trail حفظ می‌شود، اما نتیجه اصلی فعلی نیست.
  - full 400-case split judge اجرا، retry و merge شد:
    `results/judgments/paper1_main_semantic_openrouter_s400_split/merged_authoritative`.
  - نتیجه full judge:
    `total_judged=400`, `authoritative=true`, `authoritative_judgments=400`, `business_correct=161/400=0.4025`, `business_incorrect=239/400=0.5975`, `provider_error=0`, `provider_parse_error=0`, `redaction_applied=true`.
  - تفسیر نهایی:
    این artifact برای semantic/business correctness کل positive400 قابل گزارش است، اما باید جدا از strict execution accuracy گزارش شود و به‌عنوان LLM-as-judge evidence، نه human annotation، معرفی شود.

- [x] **B1.7 Final report package**
  - فایل‌ها:
    ```text
    results/reports/paper_tables.md
    results/reports/final_artifact_manifest.json
    docs/PARS_SQL_PAPER1_REPRODUCIBILITY.md
    docs/PARS_SQL_PAPER1_RESULTS_SUMMARY.md
    docs/paper/limitations.md
    ```
  - وضعیت فعلی:
    - `docs/PARS_SQL_PAPER1_RESULTS_SUMMARY.md` ساخته شد، اما بعد از B1.3 full و B1.5 باید دوباره نهایی شود.
    - `docs/PARS_SQL_PAPER1_REPRODUCIBILITY.md` ساخته شد، اما commandهای B1.5/B1.6 بعداً باید اضافه شوند.
    - `docs/paper/limitations.md` ساخته شد.
    - `results/reports/current_paper1_artifact_manifest.json` ساخته شد تا artifactهای فعلی یک‌جا باشند؛ این فایل final manifest نیست.
    - `results/reports/paper_tables.md` ساخته شد و table pack فعلی مقاله را شامل می‌شود.
    - `results/reports/final_artifact_manifest.json` ساخته شد و package فعلی را می‌بندد.

### B2. Optional یا Paper 2

- [ ] Multi-candidate adoption as default.
- [ ] Routed reliability gate برای user-facing actionها.
- [ ] QLoRA/fine-tuning.
- [ ] Edge/mobile runtime.
- [ ] Narrative/storytelling as core claim.
- [ ] Large deterministic template pack as main method.

---

## 15. Contractهای دقیق پیشنهادی برای کد

### 15.1 Dataset contracts

اگر `src/core/dataset_types.py` اضافه شود، حداقل این مدل‌ها را داشته باشد:

```python
from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class PositiveExample(BaseModel):
    id: str
    question_fa: str
    difficulty: str
    category: str
    sql: str
    expected_tables: list[str] = Field(default_factory=list)
    expected_columns: list[str] = Field(default_factory=list)
    expected_values: list[str] = Field(default_factory=list)
    expected_join_paths: list[str] = Field(default_factory=list)
    recommended_visual: str | None = None
    safe_sql: bool = True
    dialect: str = "sqlite"


class BehavioralExample(BaseModel):
    id: str
    evaluation_type: str
    user_utterance_fa: str
    should_generate_sql: bool
    expected_action: str
    expected_sql: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
```

### 15.2 Trace contracts

اگر `src/core/trace.py` اضافه شود، حداقل این مدل‌ها را داشته باشد:

```python
from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class AttemptTrace(BaseModel):
    item_id: str
    iteration: int
    ablation_id: str
    prompt: str | None = None
    raw_model_response: str | None = None
    parsed_payload: dict[str, Any] | None = None
    parsed: bool = False
    generated_sql: str | None = None
    validation_errors: list[dict[str, Any]] = Field(default_factory=list)
    execution_passed: bool = False
    execution_error: str | None = None
    repair_action: str | None = None
    latency_ms: int | None = None


class PredictionRecord(BaseModel):
    item_id: str
    question_fa: str
    normalized_question: str | None = None
    qir: dict[str, Any] | None = None
    linked_schema: dict[str, Any] | None = None
    value_links: dict[str, Any] = Field(default_factory=dict)
    retrieved_examples: list[dict[str, Any]] = Field(default_factory=list)
    generated_sql: str | None = None
    gold_sql: str | None = None
    final_action: str
    execution_correct: bool | None = None
    valid_sql: bool | None = None
    semantic_business_correct: bool | None = None
    error_category: str | None = None
    latency_ms: int
```

نکته: `src/graph/state.py::SQLAttempt` همین حالا بخش زیادی از `AttemptTrace` را پوشش می‌دهد. اگر duplication زیاد شد، `SQLAttempt` را از contract مرکزی import کن یا adapter بنویس:

```text
src/evaluation/trace_adapter.py
```

### 15.3 Error taxonomy

یک taxonomy مرکزی لازم است تا `validation`, `reflexion`, `benchmark`, `paper tables` و `judge` هرکدام نام متفاوت برای یک خطا نسازند.

فایل پیشنهادی:

```text
src/evaluation/error_taxonomy.py
```

یا اگر validation محور می‌خواهی:

```text
src/sql_validation/error_taxonomy.py
```

حداقل enum:

```python
class ErrorCategory(str, Enum):
    OUTPUT_PARSE_ERROR = "output_parse_error"
    UNSAFE_SQL = "unsafe_sql"
    NON_SELECT_SQL = "non_select_sql"
    SQL_SYNTAX_ERROR = "sql_syntax_error"
    UNKNOWN_TABLE = "unknown_table"
    UNKNOWN_COLUMN = "unknown_column"
    INVALID_JOIN_PATH = "invalid_join_path"
    WRONG_AGGREGATION = "wrong_aggregation"
    WRONG_FILTER = "wrong_filter"
    VALUE_LINKING_ERROR = "value_linking_error"
    SCHEMA_LINKING_ERROR = "schema_linking_error"
    RAG_RETRIEVAL_ERROR = "rag_retrieval_error"
    RESULT_MISMATCH = "result_mismatch"
    SEMANTIC_REVIEW_REQUIRED = "semantic_review_required"
    AMBIGUOUS_QUERY = "ambiguous_query"
    OUT_OF_SCHEMA = "out_of_schema"
    CONTROLLED_FAILURE = "controlled_failure"
```

---

## 16. Paper-Grade Command Matrix

این command matrix نسخه نهایی پیشنهادی برای تولید artifactهای مقاله است. قبل از اجرا، مدل و env را مشخص کن:

```powershell
cd D:\Project\ADHD-VTD
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:VTD_LLM_N_CTX = "8192"
$env:VTD_DEFAULT_MODEL_PATH = "D:\Project\ADHD-VTD\models\generation\<paper-model>.gguf"
```

### 16.1 Preflight

```powershell
.\.venv\Scripts\python.exe -m pytest tests\tier1_unit -q
.\.venv\Scripts\python.exe scripts\validate_dataset.py --path data\questions\full\vtd_question_sql_400_merged_validated.json
.\.venv\Scripts\python.exe scripts\validate_dataset_sql.py --path data\questions\full\vtd_question_sql_400_merged_validated.json
```

### 16.2 Gold executor

```powershell
.\.venv\Scripts\python.exe scripts\run_benchmark.py `
  --mode gold `
  --dataset positive400 `
  --sample 0 `
  --bootstrap-iterations 1000 `
  --trace-level compact `
  --ablation-id paper1_gold_positive400
```

### 16.3 Retrieval

```powershell
.\.venv\Scripts\python.exe scripts\run_benchmark.py `
  --mode retrieval `
  --dataset positive400 `
  --sample 0 `
  --retrieval-backend hybrid `
  --top-k 5 `
  --exclude-self `
  --bootstrap-iterations 1000 `
  --trace-level compact `
  --ablation-id paper1_retrieval_hybrid_positive400
```

### 16.4 Agent main

```powershell
$env:VTD_LLM_N_CTX="8192"
.\.venv\Scripts\python.exe scripts\run_benchmark.py `
  --config experiments\configs\paper1_main_local_no_templates_bounded.yaml
```

Legacy reference command, not recommended for the final full run because it uses the global retry setting:

```powershell
.\.venv\Scripts\python.exe scripts\run_benchmark.py `
  --mode agent `
  --dataset positive400 `
  --sample 0 `
  --top-k 5 `
  --exclude-self `
  --bootstrap-iterations 1000 `
  --trace-level compact `
  --ablation-id paper1_main_local_no_templates
```

### 16.5 Behavioral

```powershell
.\.venv\Scripts\python.exe scripts\run_benchmark.py `
  --mode agent `
  --dataset behavior_test `
  --sample 0 `
  --top-k 5 `
  --exclude-self `
  --bootstrap-iterations 1000 `
  --trace-level compact `
  --ablation-id paper1_behavior_test
```

### 16.6 Ablation

```powershell
.\.venv\Scripts\python.exe scripts\run_ablation.py `
  --config-dir experiments\configs `
  --output-dir results\ablation\paper1_a0_a8_final `
  --execute
```

بعد از اجرا:

```powershell
.\.venv\Scripts\python.exe scripts\analyze_ablation_manifest.py `
  results\ablation\paper1_a0_a8_final\ablation_manifest.json `
  --output-dir results\ablation\paper1_a0_a8_final
```

اگر `scripts/analyze_ablation_manifest.py` هنوز `--output-dir` ندارد، یا اضافه کن یا خروجی پیش‌فرض آن را در report مستند کن.

### 16.7 Judge subset

Offline/mock:

```powershell
.\.venv\Scripts\python.exe scripts\judge_benchmark_artifact.py `
  <paper1_main_artifact> `
  --judge-provider mock `
  --judge-policy semantic `
  --judge-sample-size 100 `
  --all-predictions
```

Cloud judge فقط با redaction و داده de-identified:

```powershell
$env:OPENROUTER_API_KEY = "<key>"
.\.venv\Scripts\python.exe scripts\judge_benchmark_artifact.py `
  <paper1_main_artifact> `
  --judge-provider openrouter `
  --judge-model qwen/qwen3.6-plus `
  --judge-policy semantic `
  --judge-sample-size 100 `
  --all-predictions
```

---

## 17. Gateهای تصمیم‌گیری برای پایان کار

### Gate A: data/gold gate

قبولی:

- `positive400` کامل load شود.
- gold SQLها execute شوند یا brokenهایشان fix/removed باشند.
- `behavioral100` از EX جدا باشد.
- dataset card نهایی باشد.

### Gate B: safety/behavior gate

قبولی:

- `unsafe_sql=0`
- `unsafe_pass_through=0`
- `safety_rejection_accuracy >= 0.8`
- `clarification_accuracy >= 0.8` یا limitation صریح اگر به آن نرسید.

### Gate C: main local gate

قبولی:

- main run local model دارد.
- `deterministic_templates=false`
- `--exclude-self=true`
- artifact کامل است.
- valid SQL، EX، reliability، latency و failure taxonomy گزارش شده‌اند.

### Gate D: ablation gate

قبولی:

- حداقل A0/A1/A2/A3/A4/A7 با same selected case hash.
- هر row artifact path دارد.
- هر flag مشخص است runtime-enforced است یا locked/metadata-only.

### Gate E: semantic judge gate

قبولی:

- failures + success sample judged شده‌اند.
- prompt version، model name، provider، redaction policy و cost ثبت شده‌اند.
- semantic و strict/reference correctness جدا گزارش شده‌اند.

### Gate F: paper packaging gate

قبولی:

- `results/reports/final_artifact_manifest.json`
- `results/reports/paper_tables.md`
- `docs/PARS_SQL_PAPER1_REPRODUCIBILITY.md`
- `docs/PARS_SQL_PAPER1_RESULTS_SUMMARY.md`
- `docs/paper/limitations.md`

---

## 18. Open Issues از `task.md` که هنوز برای مقاله مهم‌اند

این‌ها نباید در برنامه گم شوند:

1. **Phase 11 هنوز paper-grade کامل نیست.**
   - 8-case A0-A7 smoke فقط diagnostic است.
   - نیاز به suite بزرگ‌تر یا full400 ablation وجود دارد.

2. **Phase 12 behavior/output هنوز acceptance کامل ندارد.**
   - `answer_formatter.py` هست، ولی تست‌های formatter/chart/explanation کامل نیستند.
   - behavior benchmark پس از 12.1-12.3 باید rerun شود.

3. **Phase 13 reliability gate هنوز user-facing routing claim قطعی نیست.**
   - annotation-only gate قابل گزارش است.
   - routed gate باید جداگانه A/B شود.

4. **Phase 16 judge scaffold قوی شده، ولی برای مقاله نیاز به coverage متوازن دارد.**
   - failure-only A4 کافی نیست.
   - successes + failures + disputed examples لازم است.

5. **Phase 15 packaging باز است.**
   - limitations, ablation table, qualitative examples, reproduce script, final README باید بسته شوند.

6. **Phase 18.7 no-template مسیر اصلی است.**
   - template-pack high score قرنطینه است.
   - main paper باید AI/QIR/schema/retrieval pipeline بدون deterministic template overfit را گزارش کند.

7. **CLI/doc drift باید حذف شود.**
   - نمونه: `--reranker` در docs آمده ولی parser باید آن را پشتیبانی کند یا docs باید با flag واقعی هماهنگ شود.

---

## 19. نسخه نهایی مسیر اجرا برای یک برنامه‌نویس

اگر یک برنامه‌نویس تازه وارد پروژه شد، این ترتیب را دنبال کند:

1. `docs/PARS_SQL_PAPER1_IMPLEMENTATION_PLAN.md`، `task.md` و `docs/BENCHMARK_AND_TEST_GUIDE.md` را بخواند.
2. B0.1 تا B0.6 را ببندد.
3. کل unit suite را سبز کند.
4. gold positive400 را اجرا کند.
5. behavior_dev را برای safety/clarification rerun کند.
6. retrieval final را اجرا کند.
7. main local no-template را اجرا کند.
8. A0-A7/A8 ablation را با manifest اجرا کند.
9. judge subset را با redaction اجرا کند.
10. error analysis و paper tables را از artifactها بسازد.
11. final artifact manifest و reproducibility doc را تولید کند.
12. فقط بعد از این مرحله، مقاله را با نتایج واقعی بنویسد.

این ترتیب عمداً slow و evidence-first است. اگر کسی مستقیماً سراغ templateها، QLoRA یا edge runtime برود، مقاله اول دوباره از مسیر publishable خارج می‌شود.
