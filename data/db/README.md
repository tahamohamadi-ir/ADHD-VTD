# پوشه `data/db`

این پوشه لایه‌ی فیزیکی داده را نگه می‌دارد.

## فایل‌ها

- `vtd_health_research_v1.db`: دیتابیس SQLite مورد استفاده برای اجرای read-only queryها.
- `vtd_health_research_schema.sql`: تعریف SQL اسکیمای دیتابیس، مناسب برای بازسازی یا مرور ساختار جداول.

## نکته فنی

اجرای query باید همیشه با اتصال read-only انجام شود. در کد، این مسئولیت در `src/db/sqlite_connection.py` و `src/db/read_only_executor.py` پیاده‌سازی شده است. حتی اگر SQL از LLM تولید شود، قبل از رسیدن به دیتابیس باید از validatorهای امنیت، syntax و schema عبور کند.

## برای یادگیری

اول فایل schema SQL را بخوانید، بعد `data/schema/schema_snapshot.json` را با آن مقایسه کنید. این کار نشان می‌دهد پروژه چطور اسکیمای دیتابیس را به فرم قابل مصرف برای linker، validator و prompt تبدیل می‌کند.
