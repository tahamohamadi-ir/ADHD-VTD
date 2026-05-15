# پوشه `src/evaluation`

این پوشه framework ارزیابی پروژه است. هدف آن فقط محاسبه accuracy نیست؛ باید نشان دهد سیستم چه زمانی جواب می‌دهد، چه زمانی clarification می‌خواهد، چه زمانی abstain می‌کند و آیا unsafe SQL هرگز به executor می‌رسد یا نه.

## فایل‌ها

- `dataset_loader.py`: خواندن JSON/JSONL و normalize کردن caseها.
- `metrics.py`: EX، Valid SQL Rate، schema/value linking و abstention metrics.
- `reliability_metrics.py`: Reliability Score و abstention correctness.
- `benchmark_runner.py`: اجرای benchmark با تابع prediction.
- `ablation_runner.py`: اجرای experimentهای ablation.
- `gold_sql_runner.py`: اجرای SQLهای gold.
- `error_analyzer.py`: دسته‌بندی failureها.
- `human_agreement.py`: agreement و Cohen's kappa.
- `phase0_audit.py`: summary audit.
- `report_generator.py`: گزارش Markdown.

## وضعیت فعلی

طبق `task.md`، benchmark runner کامل in-progress است و ablation/statistical testing هنوز TODO است. این پوشه باید به خروجی‌های `results/benchmark` و `results/ablation` وصل شود.

## مسیر تکمیل

1. اضافه کردن `scripts/run_benchmark.py`.
2. تکمیل `error_analyzer.py` با taxonomyهای `docs/06`.
3. تکمیل `report_generator.py` برای `summary.md` و جدول‌های paper.
4. اضافه کردن `statistical_tests.py` برای bootstrap CI و McNemar.
5. اضافه کردن retrieval metrics: `Schema Recall@k`، `Value Recall@k`، `Intent@k` و `Skeleton@k`.
