# پوشه `data/rag`

این پوشه داده‌ها و indexهای retrieval را نگه می‌دارد.

## فایل‌ها و زیرپوشه‌ها

- `indexed_examples.jsonl`: منبع اصلی مثال‌های قابل بازیابی.
- `bm25/`: index واژگانی BM25.
- `chroma/`: vector store، شامل ChromaDB persistent collection یا JSON fallback.

## بازسازی indexها

```powershell
.\.venv\Scripts\python.exe scripts\build_rag_index.py --skip-vector
.\.venv\Scripts\python.exe scripts\build_rag_index.py --vector-backend json
.\.venv\Scripts\python.exe scripts\build_rag_index.py --vector-backend chroma
```

## نکته فنی

فایل‌های زیر `bm25/` و `chroma/` artifact هستند و باید از روی `indexed_examples.jsonl` قابل بازسازی باشند. برای benchmark سبک می‌توان JSON fallback را ساخت؛ برای persistent retrieval واقعی از ChromaDB استفاده می‌شود.
