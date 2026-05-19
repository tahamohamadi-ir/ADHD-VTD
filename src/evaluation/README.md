# پوشه `src/evaluation`

این پوشه framework ارزیابی پروژه است. هدف آن فقط محاسبه accuracy نیست؛ باید نشان دهد سیستم چه زمانی SQL درست تولید می‌کند، چه زمانی clarification/abstention لازم است، retrieval چه شواهدی برمی‌گرداند و خطاها با چه taxonomy قابل تحلیل هستند.

## فایل‌ها

- `dataset_loader.py`: خواندن JSON/JSONL و normalize کردن caseها به قالب مشترک evaluation.
- `metrics.py`: EX، Valid SQL Rate، schema/value linking، abstention و robustness metrics.
- `reliability_metrics.py`: Reliability Score و correctness تصمیم‌های abstention.
- `benchmark_runner.py`: اجرای benchmark با تابع prediction تزریق‌شده.
- `retrieval_metrics.py`: متریک‌های retrieval مثل `Schema Recall@k`، `Intent@k` و `Skeleton@k`.
- `export_utils.py`: خروجی CSV و جدول‌های paper-ready.
- `gold_sql_runner.py`: اجرای SQLهای gold.
- `error_analyzer.py`: دسته‌بندی failureها بر اساس error، difficulty و category.
- `human_agreement.py`: agreement و Cohen's kappa.
- `phase0_audit.py`: summary audit اولیه.
- `report_generator.py`: تولید گزارش Markdown برای Phase 0 و benchmarkهای عمومی.

## اتصال CLI

`scripts/run_benchmark.py` از این پوشه برای load dataset، محاسبه metrics، تحلیل خطا و نوشتن `summary.md` استفاده می‌کند.

```powershell
.\.venv\Scripts\python.exe scripts\run_benchmark.py --mode retrieval --dataset dev --sample 20 --top-k 3
.\.venv\Scripts\python.exe scripts\run_benchmark.py --mode gold --dataset dev --sample 20
.\.venv\Scripts\python.exe scripts\run_benchmark.py --mode agent --dataset dev --samples-per-level 1 --ablation-id full_trace
```

راهنمای عملی کامل: `docs/BENCHMARK_AND_TEST_GUIDE.md`.

## وضعیت فعلی

- benchmark runner در سطح CLI برای `retrieval`، `gold` و `agent` فعال است.
- گزارش Markdown، JSON، JSONL و CSV برای هر run ساخته می‌شود.
- retrieval-only benchmark به Phase 7 وصل شده است.
- `--samples-per-level`، progress log، bootstrap CI و prompt/raw-response trace اضافه شده‌اند.
- error analyzer هنوز taxonomy پژوهشی کامل ندارد و فقط گروه‌بندی پایه تولید می‌کند.
- ablation runner و statistical testing عمیق هنوز TODO است.

## مسیر تکمیل

1. اجرای sample-20 و balanced agent benchmark با مدل واقعی و تحلیل traceها.
2. کامل کردن `error_analyzer.py` بر اساس taxonomy فایل `docs/06_EVALUATION_ABLATION_AND_PAPER_PLAN.md`.
3. اضافه کردن `statistical_tests.py` برای McNemar و paired tests.
4. اضافه کردن `llm_judge.py` در Phase 16 برای business correctness.
5. اضافه کردن `Value Recall@k` وقتی labelهای value-link gold آماده شدند.

## تست قرارداد agent benchmark

`tests/tier2_integration/test_agent_benchmark_trace.py` مسیر `run_benchmark.py --mode agent` را با workflow mock شده اجرا می‌کند. هدف این تست این است که بدون نیاز به GPU/LLM مطمئن شویم artifactهای پژوهشی agent ساخته می‌شوند و prompt/raw response در `attempts.jsonl` باقی می‌ماند.
## Phase 11 additions

- `statistical_tests.py`: bootstrap CI and paired McNemar helpers.
- `artifact_analysis.py`: reads real `results/benchmark/...` artifacts and writes artifact-backed error-analysis reports without running a model or inventing missing labels.
- `ablation_flags.py`: classifies ablation flags as runtime-enforced, runtime-locked or metadata-only.
- `ablation_runner.py`: builds dry-run ablation manifests and optionally executes benchmark commands only when requested explicitly.
- `ablation_report.py`: reads completed ablation manifests and real benchmark summaries to generate cross-config comparison reports.
- `scripts/analyze_benchmark_artifact.py`: CLI for generating `results/error_analysis/...` reports from existing benchmark artifacts.
- `scripts/analyze_ablation_manifest.py`: CLI for generating `ablation_comparison.md/json` from a completed ablation manifest.
- `scripts/run_ablation.py`: CLI for creating ablation manifests. Default mode is dry-run and every job remains `result_status=not_run`.

Current runtime-enforced ablation flags: `nlu`, `schema_linking`, `value_linking`, `cag`, `reflexion`, `repair`.
Runtime-locked flags: `safety`, `validation`.
Metadata-only flags: none.

Verified Phase 11 first-slice artifacts:

```text
results/error_analysis/20260517_phase11_spl2_after_fixes/error_report.md
results/ablation/20260517_phase11_dry_run_manifest/ablation_manifest.json
results/ablation/20260517_phase11_a0_a7_execute/ablation_comparison.md
```

The A0-A7 comparison is a real artifact-backed smoke comparison, but it is not a final model-quality or SOTA claim.
