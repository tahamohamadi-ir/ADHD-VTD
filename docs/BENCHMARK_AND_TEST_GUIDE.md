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

بدون این env، runner از نام پیش‌فرض مدل در گزارش استفاده می‌کند؛ ولی اجرای `agent` به مدل واقعی نیاز دارد.

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

اجرای agent با تعداد مساوی از هر سطح difficulty:

```powershell
.\.venv\Scripts\python.exe scripts\run_benchmark.py --mode agent --dataset dev --samples-per-level 5 --ablation-id full_trace
```

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

## خطاهای رایج

- مدل تنظیم نشده: `VTD_DEFAULT_MODEL_PATH` را ست کنید.
- encoding فارسی خراب است: `PYTHONIOENCODING` و `Console.OutputEncoding` را تنظیم کنید.
- `--sample` و `--samples-per-level` همزمان داده شده‌اند: فقط یکی را استفاده کنید.
- artifact زیاد بزرگ شده: فعلاً Phase 10 عمداً trace کامل ذخیره می‌کند؛ بعداً `--trace-level` اضافه می‌شود.
- EX پایین است ولی Valid SQL بالاست: احتمالاً semantic/business mismatch، schema linking یا prompt context مشکل دارد.
