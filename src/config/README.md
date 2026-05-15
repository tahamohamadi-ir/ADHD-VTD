# پوشه `src/config`

این پوشه تنظیمات runtime و مسیرهای پروژه را متمرکز می‌کند.

## فایل‌ها

- `paths.py`: پیدا کردن root پروژه و تعریف مسیرهای مهم مثل `data/`, `models/`, `results/`, `DB_PATH` و `SCHEMA_DIR`.
- `settings.py`: dataclass تنظیمات برنامه، مثل مسیر مدل‌ها، timeout SQLite، retry و حالت runtime.
- `features.py`: محل feature flagها و تصمیم‌های فعال/غیرفعال.
- `__init__.py`: معرفی پوشه به‌عنوان package.

## نکته فنی

کدهای دیگر نباید مسیرها را hard-code کنند. وقتی همه از `paths.py` استفاده کنند، اجرای پروژه از script، test یا CLI behavior یکسان‌تری دارد.

## برای توسعه

اگر متغیر محیطی جدید، مسیر artifact جدید یا تنظیم runtime اضافه می‌شود، ابتدا این پوشه را به‌روز کنید و بعد آن را در ماژول مصرف‌کننده import کنید.
