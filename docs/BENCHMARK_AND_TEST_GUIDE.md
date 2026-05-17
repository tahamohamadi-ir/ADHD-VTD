# راهنمای اجرای Benchmark و Test

این سند راهنمای عملی اجرای benchmarkها، تست‌ها و خواندن خروجی‌هاست. اگر توسعه از وسط کار متوقف شد، برای ادامه اول این فایل، بعد `task.md` و بعد `docs/phases/PHASE_10_BENCHMARK_RUNNER.md` را بخوانید.

## پیش‌نیاز محیط

از ریشه پروژه اجرا کنید:

```powershell
cd D:\Project\ADHD-VTD
.\.venv\Scripts\Activate.ps1
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
```

اگر benchmark با مدل محلی اجرا می‌شود، مسیر مدل را تنظیم کنید:

```powershell
$env:VTD_DEFAULT_MODEL_PATH = "D:\Project\ADHD-VTD\models\generation\<model-file>.gguf"
```

برای promptهای طولانی‌تر، context window را هم تنظیم کنید:

```powershell
$env:VTD_LLM_N_CTX = "4096"
```

بدون این env، runner از نام پیش‌فرض مدل در گزارش استفاده می‌کند؛ ولی اجرای `agent` به مدل واقعی نیاز دارد.

### Local Model Smoke Validation

Before any Phase 10 agent benchmark, validate that the local GGUF model can be loaded and that the LangGraph generation path reaches parsing and validation.

Recommended first smoke model:

```powershell
$env:VTD_DEFAULT_MODEL_PATH = "D:\Project\ADHD-VTD\models\generation\Qwen__Qwen2.5-Coder-3B-Instruct-GGUF\qwen2.5-coder-3b-instruct-q4_k_m.gguf"
```

This 3B model is used for the first smoke because it is faster to load than the 7B model. After the smoke passes, repeat the same benchmark protocol with the target paper model, for example:

```powershell
$env:VTD_DEFAULT_MODEL_PATH = "D:\Project\ADHD-VTD\models\generation\qwen2.5-coder-7b-instruct-q4_k_m.gguf"
```

Run the smoke:

```powershell
.\.venv\Scripts\python.exe scripts\run_agent.py "درصد دانشجویان افسرده چقدر است؟" --verbose
```

Acceptance criteria:

- the model file exists and loads without a setup error;
- the run prints a final answer or a controlled failure path;
- verbose output shows generated SQL, raw model response, parsed payload, validation errors and attempt count;
- if JSON parsing fails, the raw model response must still be visible in the later benchmark trace;
- the result must be recorded in `task.md` before starting the next Phase 10 gate.

## اجرای سریع تست‌ها

تست‌های سریع و deterministic:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\tier1_unit -q
```

تست‌های هدفمند Phase 10:

```powershell
.\.venv\Scripts\python.exe -m pytest `
  tests\tier1_unit\test_dataset_loader_sampling.py `
  tests\tier1_unit\test_metrics_bootstrap.py `
  tests\tier1_unit\test_graph_attempt_trace.py `
  tests\tier1_unit\test_benchmark_artifact_contract.py -q
```

تست‌های integration:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\tier2_integration -q
```

تست integration مخصوص قرارداد trace بنچمارک agent:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\tier2_integration\test_agent_benchmark_trace.py -q
```

این تست workflow و مدل را mock می‌کند، اما مسیر واقعی `run_benchmark.py --mode agent` را اجرا می‌کند و بررسی می‌کند `config`, `predictions`, `attempts`, `summary` و prompt/raw response ذخیره شده باشند.

قاعده: هر تستی که به LLM واقعی یا benchmark طولانی نیاز دارد نباید در Tier 1 باشد.

## حالت‌های Benchmark

`scripts/run_benchmark.py` سه mode اصلی دارد:

| Mode | هدف | نیاز به LLM |
|---|---|---|
| `retrieval` | سنجش کیفیت retrieval/CAG و top-k examples | نه |
| `gold` | sanity check برای executor، metric و artifactها با gold SQL | نه |
| `agent` | اجرای کامل LangGraph و مدل محلی | بله |

### Retrieval

```powershell
.\.venv\Scripts\python.exe scripts\run_benchmark.py --mode retrieval --dataset dev --sample 20 --top-k 3
```

برای dev/test و هر run قابل استفاده در paper، self-overlap exclusion را فعال کنید:

```powershell
.\.venv\Scripts\python.exe scripts\run_benchmark.py --mode retrieval --dataset dev --sample 5 --top-k 3 --exclude-self --ablation-id manual_exclude_self_smoke
```

با vector backend:

```powershell
.\.venv\Scripts\python.exe scripts\run_benchmark.py --mode retrieval --dataset dev --sample 20 --top-k 3 --use-vector
```

### Gold

برای بررسی سریع زیرساخت بدون LLM:

```powershell
.\.venv\Scripts\python.exe scripts\run_benchmark.py --mode gold --dataset dev --sample 20
```

نمونه متوازن از هر سطح difficulty:

```powershell
.\.venv\Scripts\python.exe scripts\run_benchmark.py --mode gold --dataset dev --samples-per-level 5 --ablation-id smoke
```

### Agent

اجرای agent با ۲۰ نمونه:

```powershell
.\.venv\Scripts\python.exe scripts\run_benchmark.py --mode agent --dataset dev --sample 20 --ablation-id full_trace
```

نسخه توصیه‌شده بعد از balanced smoke و اصلاح taxonomy:

```powershell
.\.venv\Scripts\python.exe scripts\run_benchmark.py --mode agent --dataset dev --sample 20 --bootstrap-iterations 300 --ablation-id full_trace_sample20
```

اجرای agent با تعداد مساوی از هر سطح difficulty:

```powershell
.\.venv\Scripts\python.exe scripts\run_benchmark.py --mode agent --dataset dev --samples-per-level 5 --ablation-id full_trace
```

نسخه توصیه‌شده برای runهای dev/test بعد از leakage audit:

```powershell
.\.venv\Scripts\python.exe scripts\run_benchmark.py --mode agent --dataset dev --samples-per-level 5 --exclude-self --trace-level full --ablation-id full_trace_exclude_self
```

اولین اجرای واقعی پس از smoke مدل باید کوچک‌تر باشد:

```powershell
.\.venv\Scripts\python.exe scripts\run_benchmark.py --mode agent --dataset dev --samples-per-level 1 --bootstrap-iterations 100 --ablation-id full_trace
```

این run برای بستن contract خروجی است، نه ادعای کیفیت نهایی. بعد از آن `attempts.jsonl` و `failures.jsonl` را inspect کنید و نتیجه را در `task.md` ثبت کنید.

### Phase 10 Closeout Smoke

پس از shape-contract validator و گزارش خطای `results/error_analysis/20260517_phase10_shape_contract/error_report.md`، گیت باقی‌مانده Phase 10 یک smoke کمی بزرگ‌تر است. این run هنوز metric نهایی paper نیست؛ هدفش این است که artifact contract، retry/validation trace، self-overlap metadata و failure taxonomy روی نمونه متوازن بزرگ‌تر هم سالم بمانند.

```powershell
Start-Transcript -Path .\results\benchmark\manual_agent_shape_contract_spl2.log -Append

python scripts\run_benchmark.py `
  --mode agent `
  --dataset dev `
  --samples-per-level 2 `
  --bootstrap-iterations 200 `
  --exclude-self `
  --trace-level full `
  --ablation-id manual_agent_shape_contract_spl2

Stop-Transcript
```

بعد از اجرا، آخرین artifact را این‌طور پیدا و خلاصه کنید:

```powershell
$ART = Get-ChildItem .\results\benchmark -Directory |
  Where-Object { $_.Name -like "*manual_agent_shape_contract_spl2" } |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 1

$ART.FullName

$summaryPath = Get-ChildItem $ART.FullName -Filter "*_summary.json" | Select-Object -First 1
$summary = Get-Content $summaryPath.FullName -Raw | ConvertFrom-Json
$summary.dataset
$summary.metrics
$summary.reliability
$summary.latency
$summary.retrieval_self_overlap

$failuresPath = Get-ChildItem $ART.FullName -Filter "*_failures.jsonl" | Select-Object -First 1
Get-Content $failuresPath.FullName | ForEach-Object { $_ | ConvertFrom-Json } |
  Select-Object id, difficulty, category, intent, expected_action, actual_action, error, valid_sql, execution_correct, latency_ms

$attemptsPath = Get-ChildItem $ART.FullName -Filter "*_attempts.jsonl" | Select-Object -First 1
Get-Content $attemptsPath.FullName | ForEach-Object { $_ | ConvertFrom-Json } |
  Where-Object { $_.validation_passed -eq $false -or $_.error_message } |
  Select-Object case_id, attempt_index, validation_passed, sql, error_message |
  Format-List
```

قبولی این گیت یعنی run کامل شود، artifactهای نهایی بدون `partial_` ساخته شوند، prompt/raw response در attempts باشد، `unsafe_sql=0` بماند، self-overlap metadata ثبت شود و failureها taxonomy/validation message داشته باشند. پایین بودن EX به‌تنهایی Phase 10 را fail نمی‌کند؛ Phase 10 زیرساخت سنجش است. بهبود کیفیت مدل، ablation و semantic judge در فازهای بعدی ادامه پیدا می‌کند.

اجرای agent با config:

```powershell
.\.venv\Scripts\python.exe scripts\run_benchmark.py --mode agent --dataset test --samples-per-level 5 --config benchmark\configs\research_agent_v1.yaml
```

## انتخاب Dataset

Aliasهای پشتیبانی‌شده:

| Alias | مسیر |
|---|---|
| `dev` | `data/questions/dev/dev.json` |
| `test` | `data/questions/test/test.json` |
| `positive400` | `data/questions/full/vtd_question_sql_400_merged_validated.json` |
| `behavior_dev` | `data/questions/special/behavior_dev.json` |
| `behavior_test` | `data/questions/special/behavior_test.json` |
| `phase0` | `data/questions/audit/phase0_50q_audit_cases.json` |

برای فایل سفارشی:

```powershell
.\.venv\Scripts\python.exe scripts\run_benchmark.py --mode gold --path data\questions\dev\dev.json --dataset dev --sample 5
```

## Sampling

دو روش اصلی وجود دارد:

```powershell
--sample 20
--samples-per-level 5
```

`--sample` یعنی N نمونه اول dataset.  
`--samples-per-level` یعنی N نمونه از هر مقدار `difficulty` مثل `easy`, `medium`, `hard`, `complex`.

این دو flag نباید همزمان استفاده شوند.

## Log ترمینال

runner برای هر case یک خط شفاف چاپ می‌کند:

```text
[3/20] id=VTD-237 difficulty=complex category=global_change_dashboard expected=generate_sql actual=generate_sql status=fail latency=18342ms elapsed=00:01:02 eta=00:05:41
```

این log برای فهمیدن سرعت، مقدار باقی‌مانده و case خطادار کافی است. خروجی کامل در artifactها ذخیره می‌شود.

در پایان run هم runner باید یک خلاصه کوتاه چاپ کند:

```text
=== Benchmark Summary ===
evaluated=20 failures=...
execution_accuracy=...
valid_sql_rate=...
reliability_score=...
unsafe_sql=...
latency_ms mean=... median=... p95=...
artifacts=results/benchmark/...
```

اگر terminal summary و artifact summary تفاوت داشتند، `summary.json` منبع نهایی است و باید bug در چاپ terminal ثبت شود.

برای runهای طولانی agent، runner باید فایل‌های partial را بعد از هر case به‌روزرسانی کند:

```text
<prefix>_partial_predictions.jsonl
<prefix>_partial_failures.jsonl
<prefix>_partial_attempts.jsonl
```

اگر process قطع شد یا timeout خورد، این فایل‌ها منبع بررسی آخرین caseهای انجام‌شده هستند. فایل‌های نهایی بدون `partial_` فقط وقتی معتبرند که run کامل شده باشد.

## خروجی‌ها

هر run در این مسیر ذخیره می‌شود:

```text
results/benchmark/<timestamp>_<mode>_<dataset>_<model_slug>_<ablation_id>/
```

فایل‌های اصلی:

| فایل | کاربرد |
|---|---|
| `<prefix>_config.json` | config کامل run، مدل، dataset، sampling، ablation و module flags |
| `<prefix>_predictions.jsonl` | یک رکورد برای هر case |
| `<prefix>_attempts.jsonl` | prompt، raw model response، SQL و retry/repair trace |
| `<prefix>_failures.jsonl` | subset خطادار |
| `<prefix>_summary.json` | خلاصه ماشینی |
| `<prefix>_summary.md` | گزارش انسانی |
| `<prefix>_benchmark_results.csv` | جدول flat برای تحلیل |
| `<prefix>_reliability_summary.csv` | خلاصه reliability |
| `<prefix>_error_taxonomy.csv` | توزیع خطا |
| `<prefix>_paper_tables.md` | جدول‌های اولیه paper-ready |

برای debugging مدل، اول این دو فایل را باز کنید:

```text
predictions.jsonl
attempts.jsonl
```

اگر SQL غلط است، `attempts.jsonl` نشان می‌دهد prompt چه بوده و مدل دقیقاً چه پاسخ خامی داده است. اگر SQL درست اجرا می‌شود ولی پاسخ مفهومی درست نیست، آن case برای Phase 16 و LLM-as-a-Judge مهم است.

## معیارها

معیارهای static:

- `execution_accuracy`: تطابق result با gold SQL.
- `valid_sql_rate`: SQL معتبر و قابل اجرا.
- `reliability_score`: امتیاز ترکیبی پاسخ درست، abstention و safety.
- `clarification_accuracy`: تصمیم درست برای ابهام.
- `safety_rejection_accuracy`: رد درخواست unsafe.
- latency: `mean`, `median`, `p95`, `min`, `max`.
- bootstrap 95% CI برای metricهای اصلی.

تفکیک مهم:

```text
execution_correct != semantic_business_correct
```

`execution_correct` یعنی خروجی SQL با gold SQL برابر است.  
`semantic_business_correct` یعنی SQL واقعاً پاسخ درست همان سؤال فارسی است. این بخش در Phase 16 با judge کامل می‌شود.

## LLM-as-a-Judge

Phase 16 برای business correctness است و هنوز لایه اصلی اجرای benchmark نیست. قرارداد آن:

```powershell
.\.venv\Scripts\python.exe scripts\run_benchmark.py --mode agent --dataset dev --sample 20 --use-judge --judge-provider mock
```

خروجی‌های مورد انتظار آینده:

```text
<prefix>_judgments.jsonl
<prefix>_judge_reasoning.md
<prefix>_judge_costs.json
<prefix>_semantic_business_summary.csv
```

برای cloud judge، فقط داده synthetic/de-identified یا aggregate/redacted مجاز است.

## Ablation و مقایسه مدل‌ها

برای هر ablation یک `ablation-id` مشخص بدهید:

```powershell
.\.venv\Scripts\python.exe scripts\run_benchmark.py --mode agent --dataset dev --samples-per-level 5 --ablation-id A7_full
```

برای مقایسه مدل‌ها، `VTD_DEFAULT_MODEL_PATH` را عوض کنید و همان benchmark را دوباره اجرا کنید. چون model slug و ablation id در اسم artifactها ذخیره می‌شوند، خروجی‌ها قابل مقایسه می‌مانند.

## Debug Flow پیشنهادی

1. `gold` را اجرا کنید تا مطمئن شوید executor و dataset سالم‌اند.
2. `retrieval` را اجرا کنید تا context retrieval بررسی شود.
3. `agent --samples-per-level 1` را اجرا کنید.
4. اولین failure را از `failures.jsonl` انتخاب کنید.
5. همان `case_id` را در `attempts.jsonl` پیدا کنید.
6. prompt، raw response، parsed SQL و validation errors را بررسی کنید.
7. اگر SQL اجرا نمی‌شود، مسیر validator/executor را اصلاح کنید.
8. اگر SQL اجرا می‌شود ولی منطق پاسخ غلط است، آن را برای semantic judge/error taxonomy علامت بزنید.

## Leakage and Overfit Audit

قبل از claimهای paper یا اجرای test نهایی، audit زیر را اجرا کنید:

```powershell
.\.venv\Scripts\python.exe scripts\check_benchmark_leakage.py
```

خروجی‌ها:

```text
results/data_quality/benchmark_leakage_report.md
results/data_quality/benchmark_leakage_cases.jsonl
```

این audit وجود overlapهای قابل تشخیص را گزارش می‌کند، اما نبود overfit مدل یا prompt را اثبات نمی‌کند. اگر overlap جدی بین dev/test و RAG/few-shot دیده شد، قبل از benchmark نهایی باید retrieval self-match یا split leakage حذف یا محدود شود.

برای benchmarkهای agent/retrieval روی dev/test، self-overlap exclusion باید فعال باشد:

```powershell
.\.venv\Scripts\python.exe scripts\run_benchmark.py --mode agent --dataset dev --samples-per-level 5 --exclude-self
```

این policy مثال‌هایی را که `id/base_id` یا متن سؤال normalized مشابه case فعلی دارند از context حذف می‌کند و تعداد حذف‌شده‌ها را در artifactها ذخیره می‌کند.

بعد از اجرای command، این فیلدها را بررسی کنید:

```text
*_config.json: retrieval_self_overlap_policy.enabled, removed_total
*_predictions.jsonl: exclude_self_retrieval, self_overlap_removed, self_overlap_removed_ids
*_summary.json: retrieval_self_overlap
```

## خطاهای رایج

- مدل تنظیم نشده: `VTD_DEFAULT_MODEL_PATH` را ست کنید.
- `ModuleNotFoundError: No module named 'src'` when running a script directly: the script must import `scripts/_bootstrap_path.py` before importing from `src`. `run_benchmark.py` already follows this pattern; `run_agent.py` must keep the same contract.
- `TypeError: Object of type LinkedSchema is not JSON serializable`: artifact writers must convert Pydantic/dataclass objects to plain JSON before writing `predictions.jsonl`, `attempts.jsonl` or `summary.json`.
- encoding فارسی خراب است: `PYTHONIOENCODING` و `Console.OutputEncoding` را تنظیم کنید.
- `--sample` و `--samples-per-level` همزمان داده شده‌اند: فقط یکی را استفاده کنید.
- artifact زیاد بزرگ شده: `--trace-level compact` prompt و raw response را از artifact نهایی حذف می‌کند؛ برای debug و paper evidence مقدار پیش‌فرض `--trace-level full` را نگه دارید.
- EX پایین است ولی Valid SQL بالاست: احتمالاً semantic/business mismatch، schema linking یا prompt context مشکل دارد.
