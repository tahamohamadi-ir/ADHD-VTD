# پوشه `models/generation`

این پوشه مدل‌های local LLM برای تولید SQL و پاسخ را نگه می‌دارد.

## نمونه فایل‌ها

- مدل‌های GGUF مثل Qwen، Gemma و Llama.
- پوشه‌های دانلودشده از HuggingFace با cache و metadata.
- فایل‌های `.bad_*` یا `.incomplete` که نشان‌دهنده دانلود ناقص یا مدل کنارگذاشته‌شده هستند.

## نکته فنی

برای Text-to-SQL محلی، quantization و context length مهم‌اند. یک مدل کوچک سریع‌تر است، اما ممکن است schema و join پیچیده را بدتر بفهمد. نتیجه هر مدل باید با config و benchmark ثبت شود، نه با impression دستی.
