# پوشه `src/utils`

این پوشه ابزارهای عمومی و کم‌وابستگی پروژه را نگه می‌دارد.

## فایل‌ها

- `jsonl.py`: خواندن، نوشتن و append کردن فایل‌های JSONL.
- `hashing.py`: hash پایدار برای SQL، متن و resultها.
- `logging.py`: تنظیم logger و trace id برای observability.
- `timing.py`: اندازه‌گیری latency مرحله‌ای با context manager و decorator.

## نکته فنی

utility خوب باید کوچک، قابل تست و مستقل از business logic باشد. اگر یک helper شروع به شناختن intent یا schema کرد، احتمالاً باید به ماژول تخصصی خودش منتقل شود.
