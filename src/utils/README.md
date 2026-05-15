# پوشه `src/utils`

## Phase 1 Completion - 2026-05-15

ابزارهای عمومی Phase 1 فعال و تست مستقیم دارند:

- `jsonl.py`: `read_jsonl`، `iter_jsonl`، `write_jsonl`، `append_jsonl` و `append_jsonl_batch`.
- `hashing.py`: `sql_hash`، `result_hash` و `text_hash`.
- تست پوششی: `tests/tier1_unit/test_utils_jsonl_hashing.py`.

این پوشه ابزارهای عمومی و کم‌وابستگی پروژه را نگه می‌دارد.

## فایل‌ها

- `jsonl.py`: خواندن، نوشتن و append کردن فایل‌های JSONL.
- `hashing.py`: hash پایدار برای SQL، متن و resultها.
- `logging.py`: تنظیم logger و trace id برای observability.
- `timing.py`: اندازه‌گیری latency مرحله‌ای با context manager و decorator.

## نکته فنی

utility خوب باید کوچک، قابل تست و مستقل از business logic باشد. اگر یک helper شروع به شناختن intent یا schema کرد، احتمالاً باید به ماژول تخصصی خودش منتقل شود.
