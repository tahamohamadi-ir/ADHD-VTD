# پوشه `benchmark/baselines`

این پوشه برای تعریف baselineها است. baseline یعنی نسخه‌ی قابل مقایسه‌ای از سیستم که نشان می‌دهد هر component چه ارزشی اضافه کرده است.

## نمونه baselineها

- direct prompt با full schema.
- schema-only بدون RAG.
- RAG examples بدون value linking.
- full validation stack.
- rule-only یا template-based برای sanity check.

## نکته فنی

Baseline ضعیف اما دقیق تعریف‌شده از baseline مبهم بهتر است. بدون baseline، improvementهای معماری مثل CAG، QIR یا Reflexion قابل اثبات نیستند.
