# پوشه `experiments/configs`

این پوشه configهای ablation و experiment را نگه می‌دارد.

## فایل‌های فعلی

- `exp_001_zero_shot.yaml`: baseline بدون context پیشرفته.
- `exp_002_schema_only.yaml`: استفاده از schema context.
- `exp_003_rag_only.yaml`: اثر retrieval.
- `exp_004_rag_reflexion.yaml`: retrieval همراه repair/retry.
- `exp_005_full_system.yaml`: ترکیب کامل‌تر componentها.

## نکته فنی

برای paper، configها باید تغییرات را تک‌متغیره نگه دارند. اگر هم‌زمان retrieval، prompt، مدل و validator عوض شود، معلوم نیست improvement از کجا آمده است.
