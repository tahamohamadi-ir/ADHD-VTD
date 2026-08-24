# پوشه `models`

این پوشه مدل‌های محلی، manifestها و گزارش‌های integrity مربوط به مدل‌ها را نگه می‌دارد. پروژه privacy-first است، بنابراین مسیر عملیاتی آن به مدل‌های local/edge وابسته است.

## فایل‌های راهنما و manifest

- `MODEL_REGISTRY.md`: registry انسانی مدل‌ها، نقش هر مدل، مسیر و وضعیت استفاده.
- `baseline_generation_manifest.json`: manifest مدل‌های baseline generation.
- `download_manifest.json`: وضعیت دانلود مدل‌ها.
- `download_repair_manifest.json`: گزارش repair دانلودهای ناقص.
- `model_integrity_report.json`: نتیجه کنترل integrity.

## زیرپوشه‌ها

- `generation/`: مدل‌های تولید SQL، معمولاً GGUF برای llama.cpp/llama-cpp-python.
- `embeddings/` و `embedding/`: مدل‌های embedding برای retrieval.
- `reranker/` و `rerankers/`: مدل‌های reranking برای retrieval.
- `narrative/`: مدل‌های خلاصه‌سازی/روایت متنی.
- `bge-m3/`: یک مدل embedding/rerieval مشخص با فایل‌های tokenizer، ONNX و assetهای خودش.

## نکته فنی

مدل‌ها dependency سنگین هستند، نه source code. نباید بدون نیاز در Git commit شوند. اگر یک مدل در pipeline استفاده می‌شود، مسیر، نسخه، quantization، منبع و نقش آن باید در `MODEL_REGISTRY.md` ثبت شود.
