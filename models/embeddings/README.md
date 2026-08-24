# پوشه `models/embeddings`

این پوشه مدل‌های embedding را نگه می‌دارد؛ مدل‌هایی که متن پرسش، مثال‌ها، schema descriptions و business rules را به بردار تبدیل می‌کنند.

## کاربرد

- semantic retrieval برای golden examples.
- پیدا کردن aliasها یا conceptهای مشابه.
- ساخت vector store در `data/rag/chroma`.

## نکته فنی

Embedding model روی کیفیت retrieval اثر مستقیم دارد. برای فارسی و Finglish، باید جداگانه Recall@k و Value Recall@k سنجیده شود. مدل‌های `.bad_*` معمولاً دانلود یا integrity ناموفق داشته‌اند و نباید به‌عنوان گزینه فعال استفاده شوند مگر دوباره verify شوند.
