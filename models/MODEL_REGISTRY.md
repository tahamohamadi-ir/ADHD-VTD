# Model Registry

| Role | Model | Local Path | Purpose | Notes |
|---|---|---|---|---|
| SQL LLM | Qwen2.5-Coder-7B-Instruct-Q4_K_M | models/qwen2.5-coder-7b-instruct-q4_k_m.gguf | Main SQL generation | Best coding model |
| SQL LLM fallback | Qwen3-4B-Instruct-2507-Q4_K_M | models/Qwen3-4B-Instruct-2507-Q4_K_M.gguf | Lightweight generation | Faster fallback |
| Embedding | multilingual-e5-small | models/embedding/multilingual-e5-small | Persian semantic retrieval | Use query/passages prefixes if needed |
| Embedding alternative | paraphrase-multilingual-mpnet-base-v2 | models/embedding/sentence-transformers/paraphrase-multilingual-mpnet-base-v2 | Stronger multilingual embeddings | Heavier |
| Reranker | bge-reranker-base | models/reranker/bge-reranker-base | Rerank retrieved examples | Optional |
| Narrative | pn-summary-mt5-small | models/narrative/pn-summary-mt5-small | Persian summarization | Optional |
