# پوشه `src/retrieval`

این پوشه لایه Hybrid CAG/RAG پروژه است. Phase 7 اکنون کامل شده است: BM25، hybrid scoring، vector retrieval، context builder، benchmark retrieval-only و اتصال به LangGraph فعال هستند.

## فایل‌ها

- `bm25_index.py`: tokenization فارسی و BM25 retrieval با fallback داخلی اگر `rank-bm25` نصب نباشد.
- `embedding_model.py`: wrapper lazy برای SentenceTransformers با fallback deterministic hash embedding.
- `chroma_store.py`: vector store persistent با ChromaDB و fallback JSON.
- `retrieval_scorer.py`: وزن‌دهی hybrid بر اساس semantic، lexical، schema overlap، intent و skeleton.
- `hybrid_retriever.py`: API اصلی retrieval و diversity filtering.
- `context_builder.py`: تبدیل retrieved examples به few-shot prompt context.
- `reranker.py`: reranker فعلی identity است و بعدا می‌تواند model-backed شود.

## جریان runtime

```text
link_schema -> retrieve_context -> build_prompt
```

در graph فعلا `use_vector_store=False` استفاده می‌شود تا اجرای عادی agent مجبور به load مدل embedding نشود. برای benchmark یا build مستقل می‌توان vector backend را فعال کرد.

## دستورها

```powershell
.\.venv\Scripts\python.exe scripts\build_rag_index.py --skip-vector
.\.venv\Scripts\python.exe scripts\build_rag_index.py --vector-backend json
.\.venv\Scripts\python.exe scripts\build_rag_index.py --vector-backend chroma
.\.venv\Scripts\python.exe scripts\run_benchmark.py --mode retrieval --dataset dev --sample 20 --top-k 3 --use-vector
.\.venv\Scripts\python.exe -m pytest tests\tier1_unit\test_retrieval.py -q
```

## وضعیت تایید

- BM25 index از `data/rag/indexed_examples.jsonl` ساخته شد.
- JSON vector fallback ساخته شد.
- persistent ChromaDB collection در `data/rag/chroma/` ساخته شد.
- retrieval benchmark با `--use-vector` اجرا شد.
- تست‌های retrieval: `5 passed`.

## کارهای بعدی

- `Value Recall@k` بعد از آماده شدن gold value labels.
- reranker واقعی با مدل local.
- ablation بین BM25-only، vector-only و hybrid.
