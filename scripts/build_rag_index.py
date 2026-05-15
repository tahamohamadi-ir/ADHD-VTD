from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from _bootstrap_path import add_project_root_to_path

add_project_root_to_path()

from src.config.paths import INDEXED_EXAMPLES_PATH, RAG_DIR
from src.retrieval.bm25_index import BM25Index
from src.utils.jsonl import read_jsonl


def main() -> int:
    parser = argparse.ArgumentParser(description="Build local RAG indexes for PARS-SQL.")
    parser.add_argument("--input", type=Path, default=INDEXED_EXAMPLES_PATH)
    parser.add_argument("--skip-vector", action="store_true", help="Only build the BM25 index.")
    parser.add_argument(
        "--vector-backend",
        choices=("auto", "chroma", "json"),
        default="auto",
        help="Vector store backend. auto uses ChromaDB when installed and JSON otherwise.",
    )
    args = parser.parse_args()

    records = read_jsonl(args.input)
    if not records:
        print(f"No indexed examples found at {args.input}", file=sys.stderr)
        return 1

    bm25_path = RAG_DIR / "bm25" / "bm25_index.json"
    bm25 = BM25Index.from_records(records)
    bm25.save(bm25_path)

    vector_path = None
    vector_backend = None
    if not args.skip_vector:
        from src.retrieval.chroma_store import ChromaStore

        store = ChromaStore(backend=args.vector_backend)
        vector_path = store.build(records)
        vector_backend = store.active_backend

    summary = {
        "input": str(args.input),
        "record_count": len(records),
        "bm25_index": str(bm25_path),
        "vector_index": str(vector_path) if vector_path else None,
        "vector_backend": vector_backend,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
