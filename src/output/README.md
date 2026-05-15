# پوشه `src/output`

این پوشه لایه خروجی کاربر است. طبق `task.md` این بخش Phase 12 و هنوز TODO است؛ فایل‌های فعلی عمدتاً placeholder هستند.

## نقش فایل‌ها

- `answer_formatter.py`: پاسخ فارسی برای KPI، جدول، ranking، empty result، clarification و unsafe refusal.
- `chart_recommender.py`: پیشنهاد chart بر اساس result shape.
- `explanation_builder.py`: توضیح metric، filters، joins، assumptions، confidence و trace id.
- `narrative_generator.py`: روایت کنترل‌شده از نتیجه، بدون ادعای خارج از داده.

## قوانین خروجی

- خروجی نباید چیزی فراتر از query result و metadata معتبر ادعا کند.
- اگر semantic critic یا reliability gate warning بدهد، پاسخ باید warning را شفاف نشان دهد.
- برای mental-health analytics، سیستم ابزار تشخیص بالینی نیست و disclaimer باید رعایت شود.
- chart recommendation باید قابل ارزیابی با `recommended_visual` دیتاست باشد.

## معیار پذیرش

- formatter برای answer، clarify، abstain و warn خروجی استاندارد بدهد.
- chart accuracy روی مثال‌های chart/storytelling سنجیده شود.
- narrative هیچ عدد یا نتیجه hallucinated تولید نکند.
