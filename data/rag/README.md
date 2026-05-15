# پوشه `data/rag`

این پوشه artifactهای مربوط به retrieval و CAG/RAG را نگه می‌دارد.

## فایل‌ها و زیرپوشه‌ها

- `indexed_examples.jsonl`: نمایش retrieval-ready از مثال‌ها.
- `bm25/`: محل index یا خروجی‌های BM25.
- `chroma/`: محل vector store اگر Chroma فعال شود.

## وضعیت توسعه

طبق `task.md`، داده پایه retrieval آماده است، اما index builder و runtime retrieval هنوز در Phase 7 باید تکمیل شوند.

## گام‌های بعد

1. ساخت `scripts/build_rag_index.py`.
2. ساخت BM25 index در `data/rag/bm25`.
3. ساخت Chroma store در `data/rag/chroma`.
4. گزارش retrieval metrics در `results/benchmark` یا `results/data_quality`.

## نکته فنی

Retrieval باید context کم اما ارزشمند بدهد. هدف پر کردن prompt نیست؛ هدف انتخاب schema context، value links، examples و skeletonهای واقعاً مرتبط است.
