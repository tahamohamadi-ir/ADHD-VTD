# پوشه `scripts`

این پوشه ابزارهای command-line و glue code پروژه را نگه می‌دارد. scriptها معمولاً dataset را validate می‌کنند، schema تولید می‌کنند، index می‌سازند یا pipeline را از CLI اجرا می‌کنند.

## فایل‌های فعلی مهم

- `_bootstrap_path.py`: اضافه کردن root پروژه به `sys.path`.
- `run_query.py`: اجرای یک query از NLU تا generation/validation/execution.
- `run_agent.py`: اجرای workflow LangGraph.
- `validate_dataset.py`: wrapper کنترل کیفیت dataset.
- `validate_dataset_sql.py`: اجرای gold SQLها و گزارش کیفیت.
- `compare_schema_snapshots.py`: مقایسه snapshot تولیدی و frozen schema.
- `check_schema_column_references.py`: کشف table/column hallucination.
- `check_duplicate_questions.py`: پیدا کردن duplicateها.
- `convert_dataset_to_jsonl.py`: تبدیل JSON به JSONL.
- `split_dataset.py`: ساخت train/dev/test split.
- `export_schema_markdown.py`: تولید `docs/generated/SCHEMA_REFERENCE.md`.
- `expand_golden.py`: ساخت/گسترش golden و few-shot examples.
- `add_views_to_schema.py`: sync کردن viewهای دیتابیس با schema snapshot.
- `build_rag_index.py`: ساخت BM25 index و در صورت نیاز vector fallback store از `data/rag/indexed_examples.jsonl`.

## scriptهای بعدی

- `run_benchmark.py`: اجرای benchmark و ذخیره خروجی در `results/benchmark`.
- `run_ablation.py`: اجرای configهای `experiments/configs`.
- `reproduce_paper_results.py`: اجرای مسیر reproducibility برای paper/demo.

## قانون

Scriptها باید از root پروژه اجرا شوند، idempotent باشند و خروجی‌های تولیدی را در مسیرهای canonical مثل `results/` یا `docs/generated/` ذخیره کنند.
