# پوشه `src/retrieval`

این پوشه لایه retrieval و CAG/RAG پروژه است. طبق `task.md` این بخش Phase 7 و هنوز TODO است؛ فایل‌های فعلی عمدتاً اسکلت هستند و باید به یک retriever قابل ارزیابی تبدیل شوند.

## نقش فایل‌ها

- `embedding_model.py`: بارگذاری embedding model محلی از `models/`.
- `chroma_store.py`: مدیریت vector store در `data/rag/chroma`.
- `bm25_index.py`: ساخت و search index واژگانی در `data/rag/bm25`.
- `hybrid_retriever.py`: ترکیب BM25، vector search، schema overlap، intent و skeleton.
- `reranker.py`: rerank کردن candidateها با مدل reranker.
- `context_builder.py`: ساخت context نهایی برای prompt.
- `retrieval_scorer.py`: scoreدهی و fusion logic.

## طراحی مورد انتظار

این پوشه باید با `docs/04_RAG_CAG_AND_RETRIEVAL_DESIGN.md` هماهنگ باشد. context نهایی باید چهار کانال داشته باشد:

1. schema context
2. value links
3. golden SQL examples
4. SQL skeletons

## معیار پذیرش

- `scripts/build_rag_index.py` بتواند از `data/rag/indexed_examples.jsonl` index بسازد.
- `Schema Recall@k`، `Value Recall@k`، `Intent@k` و `Skeleton@k` گزارش شوند.
- context کوچک، قابل توضیح و بدون hallucinated schema باشد.
- `src/graph` بتواند retrieval را قبل از prompt building اجرا کند.
