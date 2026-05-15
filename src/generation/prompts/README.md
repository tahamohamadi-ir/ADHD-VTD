# پوشه `src/generation/prompts`

این پوشه templateهای Jinja برای تعامل با مدل زبانی را نگه می‌دارد.

## فایل‌ها

- `sql_generation.j2`: prompt اصلی تولید SQL.
- `sql_repair.j2`: prompt تعمیر SQL پس از validation یا execution error.
- `clarification.j2`: prompt پرسیدن سؤال شفاف‌سازی.
- `answer_generation.j2`: prompt تبدیل نتیجه query به پاسخ انسانی.

## نکته فنی

Prompt باید contract خروجی را صریح کند. اگر مدل باید JSON بدهد، schema آن باید در prompt روشن باشد و parser هم باید خروجی را سخت‌گیرانه بررسی کند. prompt جایگزین validator نیست.
