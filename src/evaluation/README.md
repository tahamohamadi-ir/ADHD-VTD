# پوشه `src/evaluation`

این پوشه framework ارزیابی پروژه است. هدف آن فقط محاسبه accuracy نیست؛ باید نشان دهد سیستم چه زمانی SQL درست تولید می‌کند، چه زمانی clarification/abstention لازم است، retrieval چه شواهدی برمی‌گرداند و خطاها با چه taxonomy قابل تحلیل هستند.

## فایل‌ها

- `dataset_loader.py`: خواندن JSON/JSONL و normalize کردن caseها به قالب مشترک evaluation.
- `metrics.py`: EX، Valid SQL Rate، schema/value linking، abstention و robustness metrics.
- `reliability_metrics.py`: Reliability Score و correctness تصمیم‌های abstention.
- `benchmark_runner.py`: اجرای benchmark با تابع prediction تزریق‌شده.
- `retrieval_metrics.py`: متریک‌های retrieval مثل `Schema Recall@k`، `Intent@k` و `Skeleton@k`.
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
```

## وضعیت فعلی

- benchmark runner نمونه در سطح CLI فعال است.
- گزارش Markdown و JSON برای هر run ساخته می‌شود.
- retrieval-only benchmark به Phase 7 وصل شده است.
- error analyzer هنوز taxonomy پژوهشی کامل ندارد و فقط گروه‌بندی پایه تولید می‌کند.
- ablation/statistical testing هنوز TODO است.

## مسیر تکمیل

1. اضافه کردن mode کامل `agent` برای اجرای end-to-end LangGraph.
2. کامل کردن `error_analyzer.py` بر اساس taxonomy فایل `docs/06_EVALUATION_ABLATION_AND_PAPER_PLAN.md`.
3. اضافه کردن `attempts.jsonl` برای retry/reflexion traces.
4. اضافه کردن `statistical_tests.py` برای bootstrap CI و McNemar.
5. اضافه کردن `Value Recall@k` وقتی labelهای value-link gold آماده شدند.
