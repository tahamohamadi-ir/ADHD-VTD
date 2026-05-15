# پوشه `docs/generated`

این پوشه سندهایی را نگه می‌دارد که از artifactهای پروژه تولید می‌شوند، نه اینکه دستی منبع حقیقت باشند.

## فایل‌ها

- `SCHEMA_REFERENCE.md`: reference انسانی/LLM-friendly از اسکیمای دیتابیس، تولیدشده از snapshot اسکیمای پروژه.

## نکته فنی

اگر دیتابیس یا `data/schema/schema_snapshot.json` تغییر کند، سندهای این پوشه هم باید دوباره generate شوند. این پوشه برای review و prompt context مفید است، اما source-of-truth نهایی همچنان دیتابیس و snapshotهای schema هستند.
