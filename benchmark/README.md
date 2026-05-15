# پوشه `benchmark`

این پوشه تعریف benchmark را نگه می‌دارد، نه خروجی benchmark را.

## زیرپوشه‌ها

- `configs/`: configهای benchmark و مدل/سناریو.
- `baselines/`: تعریف baselineهای مقایسه‌ای.
- `protocols/`: پروتکل‌های ارزیابی، split policy و گزارش‌گیری.

## مرز با پوشه‌های دیگر

```text
benchmark/          تعریف و پروتکل
src/evaluation/     کد اجرای ارزیابی و metricها
results/benchmark/  خروجی runها
```

## سندهای مرتبط

- `docs/06_EVALUATION_ABLATION_AND_PAPER_PLAN.md`
- `docs/09_DATASET_AND_EVALUATION_FILES_GUIDE.md`
- `DEVELOPMENT_ROADMAP.md`

## نکته فنی

هر عددی که در گزارش می‌آید باید به یک config، protocol و خروجی قابل بازتولید وصل باشد. در این پروژه 500 آیتم به معنی 500 SQL task نیست؛ behavioral examples باید با expected action سنجیده شوند.
