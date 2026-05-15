# پوشه `src/reflexion`

این پوشه برای critic، repair، retry policy و anti-loop memory طراحی شده است. طبق `task.md` منطق پایه Reflexion فعلاً داخل `src/graph/routes.py` و `src/graph/nodes/base_nodes.py` وجود دارد، اما فایل‌های این package هنوز عمدتاً placeholder هستند.

## نقش فایل‌ها

- `critic.py`: تحلیل خطای validation/execution و ساخت feedback هدفمند.
- `repair_planner.py`: تصمیم درباره deterministic repair یا regeneration.
- `retry_policy.py`: max retries، anti-loop و جلوگیری از تکرار SQL مشابه.
- `transition_memory.py`: نگهداری history attemptها.
- `error_taxonomy.py`: دسته‌بندی خطاها برای benchmark و paper.

## نکته فنی

Reflexion نباید retry کور باشد. هر تلاش باید علت مشخص داشته باشد: syntax، schema، join، aggregation، semantic mismatch، output format یا safety.

## مسیر تکمیل

1. critic feedback از graph به `critic.py` منتقل شود.
2. منطق repair deterministic با `sql_validation/sql_rewriter.py` هماهنگ شود.
3. retry policy با taxonomyهای `docs/05` و `docs/06` یکسان شود.
4. attemptها در benchmark output ذخیره شوند.
