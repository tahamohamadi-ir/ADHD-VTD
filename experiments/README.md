# پوشه `experiments`

این پوشه configهای experiment و ablation را نگه می‌دارد. تمرکز آن روی پاسخ به این سؤال است: «کدام component واقعاً کیفیت را بهتر کرده است؟»

## زیرپوشه‌ها

- `configs/`: فایل‌های YAML برای سناریوهایی مثل zero-shot، schema-only، RAG-only، RAG+reflexion و full-system.

## اولویت ablation

برای مسیر نزدیک پروژه، ablationهای زیر کافی‌اند:

- A0: direct prompt یا zero-shot.
- A1: + Persian normalization.
- A2: + schema linking.
- A3: + value linking.
- A4: + CAG examples.
- A7: + validation stack.

این ترتیب با `docs/06_EVALUATION_ABLATION_AND_PAPER_PLAN.md` و `docs/07_IMPLEMENTATION_ROADMAP_AND_REQUIREMENTS.md` هماهنگ است.

## نکته فنی

Benchmark می‌گوید چگونه بسنجیم؛ experiment می‌گوید کدام ترکیب componentها را اجرا کنیم. خروجی experiment باید در `results/` ذخیره شود.
