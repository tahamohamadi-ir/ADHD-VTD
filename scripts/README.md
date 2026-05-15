# پوشه `scripts`

این پوشه ابزارهای command-line و glue code پروژه را نگه می‌دارد. اسکریپت‌ها معمولا dataset را validate می‌کنند، schema تولید می‌کنند، index می‌سازند، agent را اجرا می‌کنند یا artifactهای benchmark را در `results/` می‌نویسند.

## فایل‌های فعلی مهم

- `_bootstrap_path.py`: اضافه کردن root پروژه به `sys.path` برای اجرای مستقیم scriptها.
- `run_query.py`: اجرای یک query از NLU تا generation/validation/execution.
- `run_agent.py`: اجرای workflow LangGraph برای یک پرسش.
- `run_benchmark.py`: اجرای benchmark قابل بازتولید در modeهای `retrieval`، `gold` و `agent`.
- `validate_dataset.py`: wrapper کنترل کیفیت dataset.
- `validate_dataset_sql.py`: اجرای gold SQLها و گزارش کیفیت.
- `compare_schema_snapshots.py`: مقایسه snapshot تولیدی و frozen schema.
- `check_schema_column_references.py`: کشف table/column hallucination در SQLهای gold.
- `check_duplicate_questions.py`: پیدا کردن duplicate ID و duplicate question.
- `convert_dataset_to_jsonl.py`: تبدیل JSON به JSONL.
- `split_dataset.py`: ساخت train/dev/test split.
- `export_schema_markdown.py`: تولید `docs/generated/SCHEMA_REFERENCE.md`.
- `expand_golden.py`: ساخت یا گسترش golden و few-shot examples.
- `add_views_to_schema.py`: sync کردن viewهای دیتابیس با schema snapshot.
- `build_rag_index.py`: ساخت BM25 index و در صورت نیاز vector fallback store از `data/rag/indexed_examples.jsonl`.

## Benchmark

```powershell
.\.venv\Scripts\python.exe scripts\build_rag_index.py --skip-vector
.\.venv\Scripts\python.exe scripts\build_rag_index.py --vector-backend chroma
.\.venv\Scripts\python.exe scripts\run_benchmark.py --mode retrieval --dataset dev --sample 20 --top-k 3
.\.venv\Scripts\python.exe scripts\run_benchmark.py --mode gold --dataset dev --sample 20
.\.venv\Scripts\python.exe scripts\run_benchmark.py --mode gold --dataset dev --samples-per-level 5 --ablation-id smoke
.\.venv\Scripts\python.exe scripts\run_benchmark.py --mode agent --dataset dev --samples-per-level 1 --ablation-id full_trace
```

حالت `retrieval` فقط کیفیت evidence retrieval را می‌سنجد و benchmark کامل تولید SQL نیست. خروجی آن شامل `retrieval_hit_rate`، `Schema Recall@k`، `Intent@k` و `Skeleton@k` است.

حالت `gold` یک sanity benchmark بدون LLM است: SQL طلایی را با خودش اجرا و مقایسه می‌کند تا executor، metricها و report generator بررسی شوند.

حالت `agent` اجرای کامل LangGraph و مدل محلی است و برای آن باید `VTD_DEFAULT_MODEL_PATH` به یک فایل GGUF معتبر اشاره کند.

## خروجی‌های benchmark

هر run در مسیر زیر ذخیره می‌شود:

```text
results/benchmark/<timestamp>_<mode>_<dataset>_<model_slug>_<ablation_id>/
```

فایل‌های اصلی:

- `<prefix>_config.json`: تنظیمات run، dataset، mode، top-k، مدل، ablation و commit.
- `<prefix>_predictions.jsonl`: رکورد کامل هر case همراه خروجی همان mode.
- `<prefix>_attempts.jsonl`: prompt، raw model response، SQL و trace تلاش‌ها.
- `<prefix>_failures.jsonl`: subset خطادار یا miss شده.
- `<prefix>_summary.json`: خلاصه ماشینی.
- `<prefix>_summary.md`: گزارش خوانا برای انسان.
- `<prefix>_retrieval_metrics.json`: فقط برای mode `retrieval`.

راهنمای کامل اجرا و تفسیر خروجی‌ها: `docs/BENCHMARK_AND_TEST_GUIDE.md`.

## scriptهای بعدی

- `run_ablation.py`: اجرای configهای `experiments/configs`.
- `reproduce_paper_results.py`: اجرای مسیر reproducibility برای paper/demo.

## قانون

Scriptها باید از root پروژه اجرا شوند، idempotent باشند و خروجی‌های تولیدی را در مسیرهای canonical مثل `results/` یا `docs/generated/` ذخیره کنند.
