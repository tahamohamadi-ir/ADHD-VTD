# پوشه `tests/tier2_integration`

این پوشه برای تست‌های integration است؛ یعنی تست‌هایی که چند component را با هم اجرا می‌کنند.

## نمونه تست مناسب

- question فارسی -> normalize -> intent -> schema link -> prompt context.
- SQL candidate -> validation pipeline -> read-only execution.
- dataset sample -> loader -> gold SQL execution -> metric.

## نکته فنی

این تست‌ها از unit کندترند، اما باید هنوز قابل اجرای مکرر باشند. اگر نیاز به مدل LLM سنگین دارند، بهتر است به tier benchmark منتقل شوند.
