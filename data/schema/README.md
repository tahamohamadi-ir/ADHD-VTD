# پوشه `data/schema`

این پوشه نسخه‌ی ساخت‌یافته و قابل مصرف از دانش اسکیمای دیتابیس را نگه می‌دارد.

## فایل‌ها

- `schema_snapshot.json`: snapshot اصلی و curate شده از جدول‌ها، ستون‌ها و metadata.
- `schema_snapshot.generated.json`: snapshot تولیدشده از دیتابیس برای مقایسه و تشخیص drift.
- `schema_graph.json`: رابطه‌ی جدول‌ها و مسیرهای join.
- `column_aliases.fa.json`: aliasهای فارسی برای نگاشت عبارت‌های کاربر به ستون‌ها.
- `business_glossary.fa.json`: واژگان دامنه و اصطلاحات کسب‌وکاری/پژوهشی.
- `metric_definitions.json`: تعریف metricهایی مثل میانگین، شمارش، نرخ و مفاهیم آماری.
- `value_dictionary.generated.json`: مقدارهای شناخته‌شده برای value linking.

## نکته فنی

Schema linking فقط match کردن اسم ستون نیست. سیستم باید عبارت فارسی کاربر، alias، metric، join path و محدودیت‌های semantic را کنار هم بگذارد. این پوشه داده‌ی خام آن تصمیم‌گیری را تامین می‌کند.

## فایل‌های مصرف‌کننده

- `src/schema/schema_registry.py`
- `src/schema/schema_loader.py`
- `src/schema/schema_linker.py`
- `src/schema/value_linker.py`
- `src/sql_validation/schema_validator.py`
