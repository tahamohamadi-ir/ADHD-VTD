# پوشه `data/golden_sql`

این پوشه مثال‌های مرجع پرسش به SQL را نگه می‌دارد.

## فایل‌ها

- `golden_examples.jsonl`: نمونه‌های gold برای ارزیابی و مقایسه.
- `few_shot_bank.jsonl`: بانک مثال‌هایی که می‌تواند در prompt یا retrieval استفاده شود.

## نکته فنی

Few-shot example باید از نظر schema، intent و skeleton SQL با پرسش فعلی مرتبط باشد. استفاده از مثال نامرتبط می‌تواند hallucination ایجاد کند یا join اشتباه را به مدل القا کند.
