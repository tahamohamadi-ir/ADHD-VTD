# پوشه `tests/tier1_unit`

این پوشه تست‌های unit سریع را نگه می‌دارد.

## پوشش فعلی

تست‌ها برای normalizerهای فارسی/عدد/تاریخ، colloquial mapping، safety و ambiguity detection، schema/value linker، query planner، SQL validators، join/aggregation validator، rewriter و executor وجود دارند.

## نکته فنی

این تست‌ها باید بدون مدل LLM و بدون network اجرا شوند. هر چیزی که deterministic است باید در این tier پوشش داده شود تا قبل از debug کردن مدل، foundation قابل اعتماد باشد.
