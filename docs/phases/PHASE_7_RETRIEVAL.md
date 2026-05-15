# Phase 7 - Hybrid CAG/RAG Retrieval

**Status:** Completed  
**Updated:** 2026-05-15  
**Scope:** BM25 retrieval, hybrid scoring, prompt context building, graph connection, initial retrieval tests, and retrieval-only benchmark artifacts.

## What Was Added

| File | Role |
|---|---|
| `src/retrieval/bm25_index.py` | Persian-aware tokenization and BM25 retrieval with fallback scoring |
| `src/retrieval/embedding_model.py` | Lazy embedding wrapper with deterministic hash fallback |
| `src/retrieval/chroma_store.py` | Persistent ChromaDB vector store with JSON fallback |
| `src/retrieval/retrieval_scorer.py` | Weighted hybrid scoring |
| `src/retrieval/hybrid_retriever.py` | Main retrieval API and diversity filter |
| `src/retrieval/context_builder.py` | Builds prompt-ready few-shot context |
| `src/evaluation/retrieval_metrics.py` | Initial retrieval metric helpers |
| `scripts/build_rag_index.py` | Builds local RAG indexes |
| `scripts/run_benchmark.py` | Runs retrieval-only benchmark and writes artifacts |
| `tests/tier1_unit/test_retrieval.py` | Unit tests for retrieval behavior |

## Current Runtime Flow

```text
link_schema
  -> retrieve_context
  -> build_prompt
  -> generate_sql
```

The graph currently uses lexical/schema-aware retrieval without vector loading by default. This keeps normal agent runs lightweight. Vector fallback can be built separately.

## Commands

```powershell
.\.venv\Scripts\python.exe scripts\build_rag_index.py --skip-vector
.\.venv\Scripts\python.exe scripts\build_rag_index.py --vector-backend json
.\.venv\Scripts\python.exe scripts\build_rag_index.py --vector-backend chroma
.\.venv\Scripts\python.exe scripts\run_benchmark.py --mode retrieval --dataset dev --sample 20 --top-k 3
.\.venv\Scripts\python.exe scripts\run_benchmark.py --mode retrieval --dataset dev --sample 20 --top-k 3 --use-vector
.\.venv\Scripts\python.exe -m pytest tests\tier1_unit\test_retrieval.py -q
```

## Verification

```text
5 retrieval tests passed
BM25 index built from 50 indexed examples
JSON vector fallback built from 50 indexed examples
Persistent ChromaDB collection built from 50 indexed examples
Retrieval sample benchmark writes config, predictions, failures, summary, and retrieval_metrics artifacts
```

## Remaining Work

- Value-link-aware `Value Recall@k` after gold value labels are available.
- Model-backed reranker.
- Ablation between BM25-only, vector-only, and hybrid retrieval.
