# پوشه `src/retrieval`

این پوشه لایه retrieval و CAG/RAG پروژه است. Phase 7 اکنون در وضعیت `IN PROGRESS` است: BM25، hybrid scoring، context builder، script ساخت index و اتصال اولیه به LangGraph پیاده‌سازی شده‌اند.

## فایل‌ها

- `bm25_index.py`: tokenization فارسی و BM25 retrieval با fallback داخلی اگر `rank-bm25` در محیط موجود نباشد.
- `embedding_model.py`: wrapper lazy برای SentenceTransformers با fallback deterministic hash embedding.
- `chroma_store.py`: vector store سبک مبتنی بر JSON؛ مسیر آماده برای تکمیل با ChromaDB.
- `retrieval_scorer.py`: وزن‌دهی hybrid بر اساس semantic، lexical، schema overlap، intent و skeleton.
- `hybrid_retriever.py`: API اصلی retrieval و diversity filtering.
- `context_builder.py`: تبدیل retrieved examples به few-shot prompt context.
- `reranker.py`: reranker فعلی identity است و بعداً می‌تواند model-backed شود.

## وضعیت فعلی

مسیر فعلی در agent:

```text
link_schema -> retrieve_context -> build_prompt
```

در graph فعلاً `use_vector_store=False` استفاده شده تا اجرای agent مجبور به load مدل embedding سنگین نباشد. script مستقل `scripts/build_rag_index.py` می‌تواند index واژگانی و در صورت نیاز vector JSON store بسازد.

## دستورهای مفید

```powershell
.\.venv\Scripts\python.exe scripts\build_rag_index.py --skip-vector
.\.venv\Scripts\python.exe -m pytest tests\tier1_unit\test_retrieval.py -q
```

## گام‌های بعد

1. persistent ChromaDB collection به‌جای JSON vector fallback.
2. retrieval-only benchmark report.
3. value-link-aware metrics مثل `Value Recall@k`.
4. reranker واقعی با مدل local.
