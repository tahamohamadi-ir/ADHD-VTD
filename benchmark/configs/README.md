# پوشه `benchmark/configs`

این پوشه configهای benchmark را نگه می‌دارد. هر config باید مشخص کند کدام مدل، کدام dataset split، چه prompt/context policy و چه validator/retry policy استفاده شده است.

## فایل‌های فعلی

فایل‌های YAML موجود سناریوهای local LLM را برای مدل‌هایی مثل Qwen، Edge 1.5B و 7B تعریف می‌کنند.

## نکته فنی

Config باید به اندازه‌ای کامل باشد که یک run بعداً قابل تکرار باشد. نام مدل، مسیر مدل، temperature، top-k retrieval، max retries و dataset split نباید در گزارش نهایی مبهم بمانند.
