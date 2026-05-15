# پوشه `src/db`

این پوشه تنها نقطه تماس کد با دیتابیس SQLite است.

## فایل‌ها

- `sqlite_connection.py`: ساخت URI read-only و connection امن به SQLite.
- `read_only_executor.py`: اجرای query با timeout، limit و ساختار نتیجه استاندارد.
- `schema_inspector.py`: استخراج schema از دیتابیس و تولید snapshot قابل مقایسه.
- `result_serializer.py`: تبدیل نتیجه query به فرم قابل hash، ذخیره و گزارش.

## نکته فنی

read-only بودن فقط یک convention نیست؛ باید در سطح connection و SQL validation اعمال شود. `mode=ro` و `PRAGMA query_only=ON` جلوی دسته‌ای از خطاها را می‌گیرند، ولی validatorها همچنان لازم‌اند.

## مرز مسئولیت

این پوشه نباید intent را تشخیص دهد، prompt بسازد یا پاسخ فارسی تولید کند. وظیفه‌اش فقط اجرای کنترل‌شده و برگرداندن نتیجه ساخت‌یافته است.
