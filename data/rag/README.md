# پوشه `data/rag`

این پوشه artifactهای مربوط به retrieval و CAG/RAG را نگه می‌دارد.

## فایل‌ها و زیرپوشه‌ها

- `indexed_examples.jsonl`: نمایش retrieval-ready از مثال‌ها.
- `bm25/`: محل index واژگانی. اکنون `bm25_index.json` با `scripts/build_rag_index.py --skip-vector` ساخته می‌شود.
- `chroma/`: محل vector store سبک فعلی و مسیر آینده ChromaDB.

## وضعیت فعلی

BM25 index از ۵۰ مثال `indexed_examples.jsonl` ساخته شد. vector store فعلاً fallback مبتنی بر JSON دارد تا توسعه بدون dependency سنگین هم قابل تست باشد.

## بازتولید index

```powershell
.\.venv\Scripts\python.exe scripts\build_rag_index.py --skip-vector
```

برای ساخت vector fallback:

```powershell
.\.venv\Scripts\python.exe scripts\build_rag_index.py
```

## نکته فنی

Retrieval باید context کم اما ارزشمند بدهد. هدف پر کردن prompt نیست؛ هدف انتخاب schema context، value links، examples و skeletonهای واقعاً مرتبط است.
