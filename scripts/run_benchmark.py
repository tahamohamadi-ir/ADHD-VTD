from __future__ import annotations

import argparse
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from _bootstrap_path import PROJECT_ROOT  # type: ignore

from src.config.paths import QUESTIONS_DIR, RESULTS_DIR
from src.config.settings import SETTINGS
from src.db.read_only_executor import ReadOnlyExecutor
from src.evaluation.dataset_loader import (
    LoadedDataset,
    load_dataset,
    load_phase0_50q_cases,
    load_positive_400,
    select_samples_per_level,
    summarize_cases,
    write_json,
    write_jsonl,
)
from src.evaluation.error_analyzer import analyze_errors
from src.evaluation.metrics import add_bootstrap_cis, aggregate_basic_metrics, latency_summary
from src.evaluation.reliability_metrics import reliability_score
from src.evaluation.report_generator import write_benchmark_markdown_report
from src.evaluation.retrieval_metrics import summarize_retrieval
from src.evaluation.export_utils import export_benchmark_csvs, generate_paper_tables
from src.retrieval.hybrid_retriever import HybridRetriever
from src.retrieval.retrieval_scorer import RetrievalQuery
from src.graph.state import VTDState
import uuid
import yaml


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


def format_duration(seconds: float) -> str:
    seconds = max(0, int(seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


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


def agent_prediction(
    case: dict[str, Any],
    workflow: Any,
    executor: ReadOnlyExecutor,
    *,
    ablation_config: dict[str, bool] | None = None,
) -> dict[str, Any]:
    question = case_question(case)
    initial_state = VTDState(
        trace_id=str(uuid.uuid4()),
        raw_question=question,
        ablation_config=ablation_config or VTDState(trace_id="tmp", raw_question="tmp").ablation_config,
    )

    started = time.perf_counter()
    # LangGraph invoke typically takes a dict
    final_state_dict = workflow.invoke(initial_state.model_dump())
    latency_ms = int((time.perf_counter() - started) * 1000)

    # Extract attempts for trace
    attempts = [a.model_dump() if hasattr(a, 'model_dump') else a for a in final_state_dict.get("attempts", [])]
    
    # Basic prediction info
    generated_sql = final_state_dict.get("generated_sql")
    gold_sql = case.get("gold_sql") or case.get("sql")
    expected_action = case.get("expected_action") or "generate_sql"
    actual_action = "generate_sql"
    
    # Determine actual_action from state
    if final_state_dict.get("final_answer"):
        answer = final_state_dict["final_answer"]
        if "ابهام" in answer or "شفاف" in answer:
            actual_action = "ask_clarification"
        elif "تلاش" in answer or "قادر" in answer:
            actual_action = "fail_gracefully"
        elif "تحلیل" in answer:
            actual_action = "format_answer"

    # Evaluation
    ok = False
    execution_correct = False
    valid_sql = not bool(final_state_dict.get("validation_errors"))
    result_hash = None
    gold_hash = None
    
    if expected_action == "generate_sql":
        if generated_sql and gold_sql:
            comparison = executor.compare_results(generated_sql, gold_sql)
            execution_correct = bool(comparison.get("match"))
            result_hash = comparison.get("generated_hash")
            gold_hash = comparison.get("gold_hash")
            ok = execution_correct
        else:
            ok = False
    else:
        # Behavioral evaluation
        # For now, simple action matching. 
        # expected_action can be safety_refusal, ambiguity_clarification, etc.
        # Mapping to actual_action
        if expected_action == "safety_refusal" and actual_action == "ask_clarification":
            ok = True # Clarification node often handles both in current base_nodes
        elif expected_action == "ambiguity_clarification" and actual_action == "ask_clarification":
            ok = True
        elif expected_action == actual_action:
            ok = True

    for attempt in attempts:
        attempt.setdefault("gold_result_hash", gold_hash)

    return {
        "actual_action": actual_action,
        "mode": "agent",
        "ok": ok,
        "action_correct": ok if expected_action != "generate_sql" else None,
        "execution_correct": execution_correct,
        "semantic_business_correct": None,
        "valid_sql": valid_sql,
        "normalized_question": final_state_dict.get("normalized_question"),
        "generated_sql": generated_sql,
        "gold_sql": gold_sql,
        "explanation": final_state_dict.get("explanation"),
        "intent": final_state_dict.get("intent"),
        "qir": final_state_dict.get("qir"),
        "linked_schema": final_state_dict.get("linked_schema"),
        "retrieved_examples": final_state_dict.get("retrieved_examples"),
        "retrieval_diagnostics": final_state_dict.get("retrieval_diagnostics"),
        "retry_count": final_state_dict.get("retry_count"),
        "latency_ms": latency_ms,
        "result_hash": result_hash,
        "gold_result_hash": gold_hash,
        "attempts": attempts,
        "error": final_state_dict.get("execution_error") or (None if ok else "BEHAVIOR_MISMATCH"),
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


def build_output_dir(config_id: str, stamp: str, output_dir: str | None = None) -> Path:
    if output_dir:
        return Path(output_dir)
    return RESULTS_DIR / "benchmark" / f"{stamp}_{slug(config_id)}"


def get_model_slug() -> str:
    if SETTINGS.default_model_path:
        return slug(Path(SETTINGS.default_model_path).stem)
    return "qwen2-5-coder-7b"


def get_model_path() -> str | None:
    return SETTINGS.default_model_path


def get_model_name() -> str:
    if SETTINGS.default_model_path:
        return Path(SETTINGS.default_model_path).stem
    return "qwen2.5-coder-7b-default"


def split_module_flags(flags: dict[str, bool]) -> tuple[list[str], list[str]]:
    enabled = sorted(k for k, v in flags.items() if bool(v))
    disabled = sorted(k for k, v in flags.items() if not bool(v))
    return enabled, disabled


def run(args: argparse.Namespace) -> Path:
    started_at = utc_now()
    dataset = load_named_dataset(args.dataset, args.path)
    if args.sample and args.samples_per_level:
        raise ValueError("Use either --sample or --samples-per-level, not both.")

    if args.samples_per_level:
        cases = select_samples_per_level(dataset.cases, args.samples_per_level)
        selection_policy = "samples_per_level"
    else:
        cases = dataset.cases[: args.sample] if args.sample else dataset.cases
        selection_policy = "first_n" if args.sample else "all"
    
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_slug = get_model_slug()
    model_name = get_model_name()
    model_path = get_model_path()
    ablation_id = args.ablation_id or "full"
    ablation_config = args.ablation_config or {
        "nlu": True,
        "schema_linking": True,
        "value_linking": True,
        "cag": True,
        "validation": True,
        "repair": True,
        "abstention": True,
        "reflexion": True,
        "reliability_gate": False,
        "llm_judge": False,
    }
    enabled_modules, disabled_modules = split_module_flags(ablation_config)
    
    config_id = args.config_id or f"{args.mode}_{args.dataset}_{model_slug}_{ablation_id}"
    output_dir = build_output_dir(config_id, stamp, args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    records: list[dict[str, Any]] = []
    total = len(cases)
    run_started = time.perf_counter()

    def log_progress(index: int, case: dict[str, Any], record: dict[str, Any]) -> None:
        elapsed = time.perf_counter() - run_started
        avg = elapsed / index if index else 0.0
        eta = avg * max(total - index, 0)
        status = "ok" if record.get("ok") or record.get("execution_correct") else "fail"
        print(
            "[{}/{}] id={} difficulty={} category={} expected={} actual={} status={} "
            "latency={}ms elapsed={} eta={}".format(
                index,
                total,
                case.get("id") or case.get("case_id") or "",
                case.get("difficulty", "unknown"),
                case.get("category", "unknown"),
                case.get("expected_action", ""),
                record.get("actual_action", ""),
                status,
                record.get("latency_ms", ""),
                format_duration(elapsed),
                format_duration(eta),
            ),
            flush=True,
        )

    if args.mode == "retrieval":
        retriever = HybridRetriever(use_vector_store=args.use_vector)
        for index, case in enumerate(cases, start=1):
            record = dict(case, **retrieval_prediction(case, retriever, top_k=args.top_k))
            records.append(record)
            log_progress(index, case, record)
    elif args.mode == "gold":
        executor = ReadOnlyExecutor()
        for index, case in enumerate(cases, start=1):
            started = time.perf_counter()
            record = dict(case, **gold_prediction(case, executor))
            record.setdefault("latency_ms", int((time.perf_counter() - started) * 1000))
            records.append(record)
            log_progress(index, case, record)
    elif args.mode == "agent":
        from src.graph.workflow import create_workflow

        workflow = create_workflow()
        executor = ReadOnlyExecutor()
        for index, case in enumerate(cases, start=1):
            record = dict(case, **agent_prediction(case, workflow, executor, ablation_config=ablation_config))
            records.append(record)
            log_progress(index, case, record)
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
        "samples_per_level": args.samples_per_level,
        "selection_policy": selection_policy,
        "top_k": args.top_k,
        "use_vector": args.use_vector,
        "model_name": model_name,
        "model_path": model_path,
        "model_slug": model_slug,
        "ablation_id": ablation_id,
        "enabled_modules": enabled_modules,
        "disabled_modules": disabled_modules,
        "module_flags": ablation_config,
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
        "latency": latency_summary(records),
    }
    if args.mode == "retrieval":
        summary["metrics"] = retrieval_basic_metrics(records)
        summary["retrieval_metrics"] = summarize_retrieval(records).to_dict()
    else:
        summary["metrics"] = add_bootstrap_cis(
            aggregate_basic_metrics(records),
            records,
            iterations=args.bootstrap_iterations,
            seed=args.seed,
        )
        summary["reliability"] = reliability_score(records).as_dict()

    # File naming with timestamp and model
    prefix = f"{stamp}_{model_slug}_{ablation_id}"
    artifact_paths = {
        "config": output_dir / f"{prefix}_config.json",
        "summary_json": output_dir / f"{prefix}_summary.json",
        "summary_md": output_dir / f"{prefix}_summary.md",
        "predictions": output_dir / f"{prefix}_predictions.jsonl",
        "failures": output_dir / f"{prefix}_failures.jsonl",
        "attempts": output_dir / f"{prefix}_attempts.jsonl",
        "benchmark_results_csv": output_dir / f"{prefix}_benchmark_results.csv",
        "reliability_summary_csv": output_dir / f"{prefix}_reliability_summary.csv",
        "error_taxonomy_csv": output_dir / f"{prefix}_error_taxonomy.csv",
        "paper_tables_md": output_dir / f"{prefix}_paper_tables.md",
    }
    if args.mode == "retrieval":
        artifact_paths["retrieval_metrics"] = output_dir / f"{prefix}_retrieval_metrics.json"

    summary["artifacts"] = {key: str(path) for key, path in artifact_paths.items()}

    write_json(artifact_paths["config"], config)
    write_jsonl(artifact_paths["predictions"], records)
    write_jsonl(artifact_paths["failures"], failures)
    
    # Write attempts trace for agent mode
    if args.mode == "agent":
        attempts_trace = []
        for record in records:
            case_id = record.get("id") or record.get("case_id")
            for i, attempt in enumerate(record.get("attempts", [])):
                # attempt is already a dict here because of the fix in agent_prediction
                attempts_trace.append({
                    "case_id": case_id,
                    "attempt_index": i,
                    **attempt
                })
        write_jsonl(artifact_paths["attempts"], attempts_trace)
    else:
        write_jsonl(artifact_paths["attempts"], [])

    write_json(artifact_paths["summary_json"], summary)
    if args.mode == "retrieval":
        write_json(artifact_paths["retrieval_metrics"], summary["retrieval_metrics"])
    
    # Export CSVs and Paper Tables
    export_benchmark_csvs(records, summary, output_dir, prefix=prefix)
    generate_paper_tables(summary, artifact_paths["paper_tables_md"])
    
    write_benchmark_markdown_report(summary, artifact_paths["summary_md"])
    return output_dir


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run reproducible project benchmarks.")
    parser.add_argument("--mode", choices=("retrieval", "gold", "agent"), default="retrieval")
    parser.add_argument(
        "--dataset",
        choices=("dev", "test", "positive400", "behavior_dev", "behavior_test", "phase0"),
        default="dev",
    )
    parser.add_argument("--path", help="Custom dataset JSON path. Overrides --dataset path.")
    parser.add_argument("--sample", type=int, help="Evaluate the first N cases. Use 0 for all.")
    parser.add_argument("--samples-per-level", type=int, help="Evaluate N cases from each difficulty level.")
    parser.add_argument("--top-k", type=int, default=3, help="Retrieval top-k.")
    parser.add_argument("--use-vector", action="store_true", help="Enable vector fallback store in retrieval mode.")
    parser.add_argument("--config-id", help="Stable identifier used in the output directory name.")
    parser.add_argument("--ablation-id", help="Ablation identifier included in output names and summaries.")
    parser.add_argument("--output-dir", help="Explicit artifact directory.")
    parser.add_argument("--config", help="Path to a benchmark YAML config file.")
    parser.add_argument("--seed", type=int, default=SETTINGS.random_seed, help="Random seed for deterministic metric resampling.")
    parser.add_argument("--bootstrap-iterations", type=int, default=1000, help="Bootstrap iterations for confidence intervals.")
    parser.set_defaults(ablation_config=None)
    return parser


def load_config_yaml(path: str) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.config:
        yaml_data = load_config_yaml(args.config)
        # Override args with yaml data where applicable
        # This is a basic mapping, can be expanded
        if "mode" in yaml_data:
            args.mode = yaml_data["mode"]
        if "dataset" in yaml_data:
            # handle dataset object or string
            ds = yaml_data["dataset"]
            if isinstance(ds, dict):
                if "split" in ds: args.dataset = ds["split"]
                if "source" in ds: args.path = ds["source"]
                if "sample_size" in ds: args.sample = ds["sample_size"]
        if "features" in yaml_data:
            feat = yaml_data["features"]
            args.ablation_config = {str(k): bool(v) for k, v in feat.items() if isinstance(v, bool)}
            if "max_retries" in feat:
                # We can't easily change SETTINGS at runtime globally for all modules
                # but we can pass it to agent_prediction if we modify it.
                pass
        if "config_id" in yaml_data:
            args.config_id = yaml_data["config_id"]
        if "ablation_id" in yaml_data:
            args.ablation_id = yaml_data["ablation_id"]
        if "sampling" in yaml_data and isinstance(yaml_data["sampling"], dict):
            sampling = yaml_data["sampling"]
            if "samples_per_level" in sampling:
                args.samples_per_level = sampling["samples_per_level"]
            if "sample" in sampling:
                args.sample = sampling["sample"]

    if args.sample == 0:
        args.sample = None
    output_dir = run(args)
    print(f"Benchmark artifacts written to: {output_dir}")


if __name__ == "__main__":
    main()
