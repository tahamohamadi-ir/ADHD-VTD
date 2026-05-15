# پوشه `data`

این پوشه منبع داده‌ی پروژه است: دیتابیس SQLite، snapshotهای اسکیمای دیتابیس، دیتاست‌های پرسش/SQL، گزارش‌های audit و artifactهای آماده برای retrieval.

## زیرپوشه‌ها

- `db/`: دیتابیس واقعی و فایل SQL اسکیمای آن.
- `schema/`: نمایش JSON از اسکیمای دیتابیس، aliasها، glossary و تعریف metricها.
- `questions/`: مجموعه پرسش‌های train/dev/test/full/special/audit.
- `golden_sql/`: مثال‌های معتبر question-to-SQL برای few-shot و ارزیابی.
- `rag/`: داده‌های آماده‌ی retrieval، مثل مثال‌های index شده و محل indexهای BM25/Chroma.
- `audit/`: گزارش‌های کنترل کیفیت داده و اسکیمای پروژه.

## نکته فنی

در یک سیستم Text-to-SQL، دیتابیس تنها منبع حقیقت است. فایل‌های `schema_snapshot.json` و `schema_graph.json` باید با دیتابیس هماهنگ باشند؛ اگر مدل یا prompt نام ستون یا جدول اشتباه بسازد، validatorها باید آن را رد کنند.

## قرارداد نگهداری

داده‌های تولیدی و benchmark output نباید با داده‌های مرجع مخلوط شوند. خروجی اجراها باید در `results/` ذخیره شود، نه در `data/`.
