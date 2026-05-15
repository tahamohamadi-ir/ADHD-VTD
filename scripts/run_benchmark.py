from __future__ import annotations

import argparse
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from _bootstrap_path import PROJECT_ROOT

from src.config.paths import QUESTIONS_DIR, RESULTS_DIR
from src.db.read_only_executor import ReadOnlyExecutor
from src.evaluation.dataset_loader import (
    LoadedDataset,
    load_dataset,
    load_phase0_50q_cases,
    load_positive_400,
    summarize_cases,
    write_json,
    write_jsonl,
)
from src.evaluation.error_analyzer import analyze_errors
from src.evaluation.metrics import aggregate_basic_metrics
from src.evaluation.reliability_metrics import reliability_score
from src.evaluation.report_generator import write_benchmark_markdown_report
from src.evaluation.retrieval_metrics import summarize_retrieval
from src.retrieval.hybrid_retriever import HybridRetriever
from src.retrieval.retrieval_scorer import RetrievalQuery


DATASET_ALIASES = {
    "dev": QUESTIONS_DIR / "dev" / "dev.json",
    "test": QUESTIONS_DIR / "test" / "test.json",
    "behavior_dev": QUESTIONS_DIR / "special" / "behavior_dev.json",
    "behavior_test": QUESTIONS_DIR / "special" / "behavior_test.json",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def slug(value: str) -> str:
    keep = []
    for char in value.lower():
        if char.isalnum():
            keep.append(char)
        elif char in {"-", "_"}:
            keep.append(char)
        else:
            keep.append("_")
    return "".join(keep).strip("_") or "benchmark"


def git_commit() -> str | None:
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=PROJECT_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
    except Exception:
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.strip() or None


def load_named_dataset(name: str, path: str | None = None) -> LoadedDataset:
    if path:
        return load_dataset(path, kind=name)
    if name == "phase0":
        return load_phase0_50q_cases()
    if name == "positive400":
        return load_positive_400()
    if name in DATASET_ALIASES:
        return load_dataset(DATASET_ALIASES[name], kind=name)
    raise ValueError(f"Unknown dataset '{name}'. Use --path for custom datasets.")


def infer_sql_references(sql: str | None) -> tuple[list[str], list[str]]:
    if not sql:
        return [], []
    try:
        import sqlglot
        from sqlglot import exp

        parsed = sqlglot.parse_one(sql, read="sqlite")
        tables = sorted({table.name for table in parsed.find_all(exp.Table) if table.name})
        columns = sorted({column.name for column in parsed.find_all(exp.Column) if column.name})
        return tables, columns
    except Exception:
        return [], []


def case_question(case: dict[str, Any]) -> str:
    return str(case.get("question") or case.get("question_fa") or case.get("user_utterance_fa") or "")


def retrieval_prediction(case: dict[str, Any], retriever: HybridRetriever, *, top_k: int) -> dict[str, Any]:
    expected_tables, expected_columns = infer_sql_references(case.get("gold_sql") or case.get("sql"))
    expected_intent = case.get("intent") or case.get("expected_intent")
    expected_skeleton = case.get("skeleton") or case.get("expected_skeleton")
    query = RetrievalQuery(
        text=case_question(case),
        intent=expected_intent,
        tables=expected_tables,
        columns=expected_columns,
        skeleton=expected_skeleton,
    )
    started = time.perf_counter()
    retrieved = retriever.retrieve(query, top_k=top_k)
    latency_ms = int((time.perf_counter() - started) * 1000)
    retrieved_dicts = [item.to_dict() for item in retrieved]

    expected_table_set = {value.lower() for value in expected_tables}
    expected_column_set = {value.lower() for value in expected_columns}
    retrieved_tables: set[str] = set()
    retrieved_columns: set[str] = set()
    for item in retrieved_dicts:
        record = item.get("record", {})
        retrieved_tables.update(str(value).lower() for value in record.get("tables", []))
        retrieved_columns.update(str(value).lower() for value in record.get("columns", []))

    has_expected_schema = bool(expected_table_set or expected_column_set)
    schema_hit = bool((expected_table_set & retrieved_tables) or (expected_column_set & retrieved_columns))
    ok = schema_hit if has_expected_schema else bool(retrieved_dicts)
    return {
        "actual_action": "retrieve_context",
        "mode": "retrieval",
        "ok": ok,
        "retrieval_hit": ok,
        "retrieved": retrieved_dicts,
        "expected_tables": expected_tables,
        "expected_columns": expected_columns,
        "expected_intent": expected_intent,
        "expected_skeleton": expected_skeleton,
        "latency_ms": latency_ms,
        "error": None if ok else "RETRIEVAL_MISS",
    }


def gold_prediction(case: dict[str, Any], executor: ReadOnlyExecutor) -> dict[str, Any]:
    gold_sql = case.get("gold_sql") or case.get("sql")
    if not gold_sql:
        return {
            "actual_action": "ask_clarification",
            "mode": "gold",
            "ok": False,
            "execution_correct": False,
            "valid_sql": False,
            "generated_sql": None,
            "error": "MISSING_GOLD_SQL",
        }
    comparison = executor.compare_results(gold_sql, gold_sql)
    ok = bool(comparison.get("match"))
    return {
        "actual_action": "generate_sql",
        "mode": "gold",
        "ok": ok,
        "execution_correct": ok,
        "valid_sql": bool(comparison.get("generated_ok") and comparison.get("gold_ok")),
        "generated_sql": gold_sql,
        "gold_sql": gold_sql,
        "result_hash": comparison.get("generated_hash"),
        "gold_result_hash": comparison.get("gold_hash"),
        "error": None if ok else comparison.get("generated_error") or comparison.get("gold_error") or "RESULT_MISMATCH",
    }


def retrieval_basic_metrics(records: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(records)
    hits = sum(1 for record in records if record.get("retrieval_hit"))
    misses = total - hits
    value = 0.0 if total == 0 else hits / total
    return {
        "retrieval_hit_rate": {
            "name": "retrieval_hit_rate",
            "value": value,
            "numerator": hits,
            "denominator": total,
            "description": "Cases where top-k retrieval overlaps expected schema or returns context when no gold SQL exists",
        },
        "retrieval_miss_rate": {
            "name": "retrieval_miss_rate",
            "value": 0.0 if total == 0 else misses / total,
            "numerator": misses,
            "denominator": total,
            "description": "Cases where retrieval did not find expected evidence",
        },
    }


def build_output_dir(config_id: str, output_dir: str | None = None) -> Path:
    if output_dir:
        return Path(output_dir)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return RESULTS_DIR / "benchmark" / f"{stamp}_{slug(config_id)}"


def run(args: argparse.Namespace) -> Path:
    started_at = utc_now()
    dataset = load_named_dataset(args.dataset, args.path)
    cases = dataset.cases[: args.sample] if args.sample else dataset.cases
    config_id = args.config_id or f"{args.mode}_{args.dataset}"
    output_dir = build_output_dir(config_id, args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.mode == "retrieval":
        retriever = HybridRetriever(use_vector_store=args.use_vector)
        records = [dict(case, **retrieval_prediction(case, retriever, top_k=args.top_k)) for case in cases]
    elif args.mode == "gold":
        executor = ReadOnlyExecutor()
        records = [dict(case, **gold_prediction(case, executor)) for case in cases]
    else:  # pragma: no cover - argparse enforces choices.
        raise ValueError(f"Unsupported mode: {args.mode}")

    failures = [
        record
        for record in records
        if not (record.get("ok") or record.get("execution_correct") or record.get("result_match"))
    ]
    dataset_summary = summarize_cases(cases)
    config = {
        "config_id": config_id,
        "mode": args.mode,
        "dataset": args.dataset,
        "dataset_path": str(dataset.path),
        "sample": args.sample or len(cases),
        "top_k": args.top_k,
        "use_vector": args.use_vector,
        "started_at": started_at,
        "finished_at": utc_now(),
        "git_commit": git_commit(),
    }
    summary: dict[str, Any] = {
        "config": config,
        "dataset": {
            "path": str(dataset.path),
            "kind": dataset.kind,
            "total_loaded": dataset.total,
            "total_evaluated": len(cases),
            **dataset_summary,
        },
        "error_analysis": analyze_errors(records).as_dict(),
    }
    if args.mode == "retrieval":
        summary["metrics"] = retrieval_basic_metrics(records)
        summary["retrieval_metrics"] = summarize_retrieval(records).to_dict()
    else:
        summary["metrics"] = aggregate_basic_metrics(records)
        summary["reliability"] = reliability_score(records).as_dict()

    artifact_paths = {
        "config": output_dir / "config.json",
        "summary_json": output_dir / "summary.json",
        "summary_md": output_dir / "summary.md",
        "predictions": output_dir / "predictions.jsonl",
        "failures": output_dir / "failures.jsonl",
    }
    if args.mode == "retrieval":
        artifact_paths["retrieval_metrics"] = output_dir / "retrieval_metrics.json"

    summary["artifacts"] = {key: str(path) for key, path in artifact_paths.items()}

    write_json(artifact_paths["config"], config)
    write_jsonl(artifact_paths["predictions"], records)
    write_jsonl(artifact_paths["failures"], failures)
    write_json(artifact_paths["summary_json"], summary)
    if args.mode == "retrieval":
        write_json(artifact_paths["retrieval_metrics"], summary["retrieval_metrics"])
    write_benchmark_markdown_report(summary, artifact_paths["summary_md"])
    return output_dir


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run reproducible project benchmarks.")
    parser.add_argument("--mode", choices=("retrieval", "gold"), default="retrieval")
    parser.add_argument(
        "--dataset",
        choices=("dev", "test", "positive400", "behavior_dev", "behavior_test", "phase0"),
        default="dev",
    )
    parser.add_argument("--path", help="Custom dataset JSON path. Overrides --dataset path.")
    parser.add_argument("--sample", type=int, default=20, help="Evaluate the first N cases. Use 0 for all.")
    parser.add_argument("--top-k", type=int, default=3, help="Retrieval top-k.")
    parser.add_argument("--use-vector", action="store_true", help="Enable vector fallback store in retrieval mode.")
    parser.add_argument("--config-id", help="Stable identifier used in the output directory name.")
    parser.add_argument("--output-dir", help="Explicit artifact directory.")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.sample == 0:
        args.sample = None
    output_dir = run(args)
    print(f"Benchmark artifacts written to: {output_dir}")


if __name__ == "__main__":
    main()
