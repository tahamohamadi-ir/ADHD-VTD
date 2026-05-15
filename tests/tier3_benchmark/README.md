# پوشه `tests/tier3_benchmark`

این پوشه برای تست‌های benchmark و regression سنگین‌تر است.

## کاربرد

- اجرای sample benchmark.
- مقایسه خروجی با baseline قبلی.
- تست latency یا reliability روی مجموعه کوچک.
- اطمینان از اینکه تغییر prompt یا validator باعث افت شدید نشده است.

## نکته فنی

این tier ممکن است به مدل محلی و دیتابیس کامل نیاز داشته باشد، پس نباید با unit tests روزمره قاطی شود.
