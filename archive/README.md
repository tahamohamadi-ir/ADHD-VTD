# پوشه `archive`

این پوشه فایل‌ها، scriptها و backupهای تاریخی را نگه می‌دارد. محتوای آن برای فهم مسیر توسعه مفید است، اما source-of-truth فعلی پروژه نیست.

## زیرپوشه‌ها

- `scripts_legacy/`: scriptهای قدیمی اجرای phaseها، patchها، تست‌های دستی و ابزارهای موقت.
- `src/`: backupهای قدیمی از `config` و `core` مربوط به Phase 0.

## اسنپ‌شات‌های cleanup منتقل‌شده

- `cleanup_20260626/` و `cleanup_20260626_round2/` در تاریخ 2026-08-24 به
  `_DELETE_REVIEW/archive/` منتقل شدند (move-only؛ لاگ: `_DELETE_REVIEW/_manifest.csv`).
  این اسنپ‌شات‌ها ignore شده بودند و جزو archive فعال نبودند.

## نکته فنی

قبل از استفاده از فایل‌های archive، نسخه فعلی همان مسئولیت را در `src/` یا `scripts/` بررسی کنید. archive برای مراجعه تاریخی است، نه برای import مستقیم یا اجرای روزمره.
