from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from _bootstrap_path import PROJECT_ROOT  # type: ignore

from src.config.paths import MODELS_DIR, QUESTIONS_DIR, RESULTS_DIR
from src.config.settings import SETTINGS
from src.db.read_only_executor import ReadOnlyExecutor
from src.evaluation.dataset_loader import (
    LoadedDataset,
    load_dataset,
    load_phase0_50q_cases,
    load_positive_400,
    select_samples_per_level,
    summarize_cases,
    to_jsonable,
    write_json,
    write_jsonl,
)
from src.evaluation.ablation_flags import ablation_runtime_contract, normalize_feature_flags
from src.evaluation.action_normalizer import (
    SQL_POSITIVE_ACTIONS,
    actions_match,
    normalize_actual_action,
    normalize_expected_action,
)
from src.evaluation.error_analyzer import analyze_errors
from src.evaluation.metrics import (
    add_bootstrap_cis,
    aggregate_basic_metrics,
    latency_summary,
    partial_credit_semantic_score,
)
from src.evaluation.reliability_metrics import reliability_score
from src.evaluation.reliability_gate import evaluate_reliability_gate
from src.evaluation.sql_consistency_critic import analyze_question_sql_consistency
from src.evaluation.trace_adapter import validate_benchmark_trace_contract
from src.evaluation.report_generator import write_benchmark_markdown_report
from src.evaluation.retrieval_metrics import summarize_retrieval
from src.evaluation.export_utils import export_benchmark_csvs, generate_paper_tables
from src.evaluation.llm_judge import judge_benchmark_artifact
from src.retrieval.hybrid_retriever import HybridRetriever
from src.retrieval.reranker import (
    CrossEncoderReranker,
    IdentityReranker,
    create_reranker,
    resolve_reranker_backend,
)
from src.retrieval.retrieval_scorer import RetrievalQuery
from src.retrieval.schema_evidence import ensure_schema_evidence_after_filter
from src.retrieval.self_overlap import filter_self_overlaps
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


def build_artifact_manifest(
    output_dir: Path,
    summary: dict[str, Any],
    artifact_paths: dict[str, Path],
) -> dict[str, Any]:
    config = summary.get("config") if isinstance(summary.get("config"), dict) else {}
    metrics = summary.get("metrics") if isinstance(summary.get("metrics"), dict) else {}
    manifest_key = str(config.get("config_id") or config.get("ablation_id") or output_dir.name)
    artifact_entry = {
        "result_status": "completed",
        "artifact_dir": str(output_dir),
        "config_id": config.get("config_id"),
        "ablation_id": config.get("ablation_id"),
        "mode": config.get("mode"),
        "dataset": config.get("dataset"),
        "dataset_hash": config.get("dataset_hash"),
        "selected_cases_hash": config.get("selected_cases_hash"),
        "model_name": config.get("model_name"),
        "model_path": config.get("model_path"),
        "model_slug": config.get("model_slug"),
        "prompt_template": config.get("prompt_template"),
        "module_flags": config.get("module_flags"),
        "deterministic_templates": (config.get("module_flags") or {}).get(
            "deterministic_templates"
        ),
        "git_commit": config.get("git_commit"),
        "started_at": config.get("started_at"),
        "finished_at": config.get("finished_at"),
        "artifacts": {key: str(path) for key, path in artifact_paths.items()},
        "metrics": {
            key: {
                "value": value.get("value"),
                "numerator": value.get("numerator"),
                "denominator": value.get("denominator"),
            }
            for key, value in metrics.items()
            if isinstance(value, dict)
        },
    }
    return {
        "schema_version": "pars_sql_benchmark_artifact_manifest_v1",
        "generated_at": utc_now(),
        "anti_fake_policy": (
            "This manifest records completed benchmark artifacts only. "
            "Config-only, dry-run, smoke, failed judge, and placeholder reranker outputs "
            "must not be cited as final paper results."
        ),
        "completed": {manifest_key: artifact_entry},
        "runs": [artifact_entry],
    }


def sha256_file(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_jsonable(value: Any) -> str:
    payload = json.dumps(
        to_jsonable(value), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


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
    return str(
        case.get("question") or case.get("question_fa") or case.get("user_utterance_fa") or ""
    )


def retrieval_prediction(
    case: dict[str, Any],
    retriever: HybridRetriever,
    *,
    top_k: int,
    exclude_self: bool = False,
    use_reranker: bool = False,
    reranker_name: str | None = None,
    reranker_obj: IdentityReranker | CrossEncoderReranker | None = None,
) -> dict[str, Any]:
    expected_tables, expected_columns = infer_sql_references(
        case.get("gold_sql") or case.get("sql")
    )
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
    retrieval_top_k = max(top_k * 5, top_k) if exclude_self else top_k
    retrieved = retriever.retrieve(
        query, top_k=retrieval_top_k, candidate_pool_size=max(25, retrieval_top_k * 2)
    )
    removed_ids: list[str] = []
    if exclude_self:
        retrieved, removed_ids = filter_self_overlaps(
            retrieved,
            case_id=case.get("id") or case.get("case_id"),
            question=case_question(case),
        )
        retrieved = ensure_schema_evidence_after_filter(retrieved, top_k=top_k)
        retrieved = retrieved[:top_k]
    if use_reranker:
        reranker_backend_value = (
            "cross_encoder" if isinstance(reranker_obj, CrossEncoderReranker) else "identity"
        )
        if isinstance(reranker_obj, CrossEncoderReranker):
            retrieved = reranker_obj.rerank(retrieved, top_k=top_k, query=case_question(case))
        else:
            retrieved = IdentityReranker().rerank(retrieved, top_k=top_k)
    else:
        reranker_backend_value = None
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
    schema_hit = bool(
        (expected_table_set & retrieved_tables) or (expected_column_set & retrieved_columns)
    )
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
        "exclude_self_retrieval": exclude_self,
        "self_overlap_removed": len(removed_ids),
        "self_overlap_removed_ids": removed_ids,
        "retrieval_reranker": reranker_name if use_reranker else None,
        "retrieval_reranker_backend": reranker_backend_value,
        "retrieval_reranker_warning": (
            "model_backed_reranker_not_implemented_identity_placeholder_used"
            if use_reranker
            and reranker_backend_value == "identity"
            and reranker_name not in {None, "identity"}
            else None
        ),
    }


def apply_agent_retrieval_overrides(
    ablation_config: dict[str, Any],
    *,
    retrieval_backend: str | None,
    reranker_name: str | None,
) -> dict[str, Any]:
    """Inject agent-mode retrieval overrides into the ablation config copy."""
    if not retrieval_backend and not (reranker_name and reranker_name != "none"):
        return ablation_config
    overridden = dict(ablation_config)
    if retrieval_backend:
        overridden["retrieval_backend"] = str(retrieval_backend)
    if reranker_name and reranker_name != "none":
        overridden["reranker"] = str(reranker_name)
    return overridden


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
        "error": (
            None
            if ok
            else comparison.get("generated_error")
            or comparison.get("gold_error")
            or "RESULT_MISMATCH"
        ),
    }


def _near_miss_partial_credit(
    executor: Any, generated_sql: str, gold_sql: str, comparison: dict[str, Any]
) -> float | None:
    """Separate-metric family: near-miss credit for SQL that ran but mismatched.

    Never mixed into EX or the reliability score (AGENTS metric-family rule).
    """
    if comparison.get("match"):
        return 1.0
    if not (comparison.get("generated_ok") and comparison.get("gold_ok")):
        return None
    try:
        gen = executor.execute_readonly(generated_sql)
        gold = executor.execute_readonly(gold_sql)
        if not (gen.ok and gold.ok):
            return None
        return round(partial_credit_semantic_score(gold.rows, gen.rows), 4)
    except Exception:  # noqa: BLE001 - diagnostic metric must never break a run
        return None


def classify_agent_error(
    *,
    expected_action: str,
    actual_action: str,
    generated_sql: str | None,
    gold_sql: str | None,
    valid_sql: bool,
    execution_correct: bool,
    final_state: dict[str, Any],
) -> str | None:
    expected_action_normalized = normalize_expected_action(expected_action)
    if expected_action_normalized in SQL_POSITIVE_ACTIONS:
        if not generated_sql:
            return "MISSING_GENERATED_SQL"
        if not valid_sql:
            return "INVALID_SQL"
        if gold_sql and not execution_correct:
            return "RESULT_MISMATCH"
        execution_error = final_state.get("execution_error")
        if execution_error:
            return "EXECUTION_ERROR"
        return None

    if not actions_match(expected_action_normalized, actual_action, generated_sql=generated_sql):
        return "ACTION_MISMATCH"
    return None


def classify_agent_exception(exc: Exception) -> str:
    message = str(exc)
    if "exceed context window" in message or "Requested tokens" in message:
        return "MODEL_CONTEXT_OVERFLOW"
    return "AGENT_EXCEPTION"


def _dict_or_none(value: Any) -> dict[str, Any] | None:
    if hasattr(value, "model_dump"):
        value = value.model_dump()
    return value if isinstance(value, dict) else None


def _latency_ms_from_payload(value: Any) -> int | None:
    payload = _dict_or_none(value)
    if not payload:
        return None
    try:
        parsed = int(payload.get("latency_ms"))
    except (TypeError, ValueError):
        return None
    return parsed if parsed >= 0 else None


def exception_prediction(
    case: dict[str, Any],
    exc: Exception,
    *,
    latency_ms: int,
    exclude_self_retrieval: bool = False,
) -> dict[str, Any]:
    gold_sql = case.get("gold_sql") or case.get("sql")
    expected_action = case.get("expected_action") or "generate_sql"
    expected_action_normalized = normalize_expected_action(
        expected_action,
        should_generate_sql=case.get("should_generate_sql"),
    )
    actual_action = "fail_gracefully"
    actual_action_normalized = normalize_actual_action(actual_action)
    action_correct = actions_match(expected_action_normalized, actual_action)
    return {
        "actual_action": actual_action,
        "actual_action_normalized": actual_action_normalized,
        "expected_action_normalized": expected_action_normalized,
        "mode": "agent",
        "ok": False,
        "action_correct": action_correct,
        "execution_correct": False,
        "semantic_business_correct": None,
        "valid_sql": False,
        "normalized_question": None,
        "generated_sql": None,
        "gold_sql": gold_sql,
        "explanation": None,
        "intent": None,
        "qir": None,
        "linked_schema": None,
        "retrieved_examples": [],
        "retrieval_diagnostics": [],
        "exclude_self_retrieval": exclude_self_retrieval,
        "self_overlap_removed": 0,
        "self_overlap_removed_ids": [],
        "retry_count": None,
        "validation_issues": [],
        "execution_error": None,
        "execution_passed": False,
        "max_retries": None,
        "final_answer": None,
        "trace_id": None,
        "latency_ms": latency_ms,
        "result_hash": None,
        "gold_result_hash": None,
        "attempts": [],
        "error": classify_agent_exception(exc),
        "exception_type": type(exc).__name__,
        "exception_message": str(exc),
    }


def agent_prediction(
    case: dict[str, Any],
    workflow: Any,
    executor: ReadOnlyExecutor,
    *,
    ablation_config: dict[str, Any] | None = None,
    exclude_self_retrieval: bool = False,
    top_k: int = 5,
    max_retries_override: int | None = None,
) -> dict[str, Any]:
    question = case_question(case)
    initial_state = VTDState(
        trace_id=str(uuid.uuid4()),
        raw_question=question,
        benchmark_case_id=str(case.get("id") or case.get("case_id") or ""),
        exclude_self_retrieval=exclude_self_retrieval,
        retrieval_top_k=top_k,
        max_retries=SETTINGS.max_retries if max_retries_override is None else max_retries_override,
        ablation_config=ablation_config
        or VTDState(trace_id="tmp", raw_question="tmp").ablation_config,
    )

    started = time.perf_counter()
    # LangGraph invoke typically takes a dict
    final_state_dict = workflow.invoke(initial_state.model_dump())
    latency_ms = int((time.perf_counter() - started) * 1000)

    # Extract attempts for trace
    attempts = [
        a.model_dump() if hasattr(a, "model_dump") else a
        for a in final_state_dict.get("attempts", [])
    ]

    # Basic prediction info
    generated_sql = final_state_dict.get("generated_sql")
    gold_sql = case.get("gold_sql") or case.get("sql")
    expected_action = case.get("expected_action") or "generate_sql"
    expected_action_normalized = normalize_expected_action(
        expected_action,
        should_generate_sql=case.get("should_generate_sql"),
    )
    actual_action = "generate_sql"

    # Determine actual_action from state
    if final_state_dict.get("actual_action"):
        actual_action = final_state_dict["actual_action"]
    elif final_state_dict.get("final_answer"):
        answer = final_state_dict["final_answer"]
        if "ابهام" in answer or "شفاف" in answer:
            actual_action = "ask_clarification"
        elif "تلاش" in answer or "قادر" in answer:
            actual_action = "fail_gracefully"
        elif "امنیتی" in answer or "خطرناک" in answer:
            actual_action = "refuse_unsafe_sql"
        elif "تحلیل" in answer:
            actual_action = "format_answer"

    # Evaluation
    ok = False
    execution_correct = False
    valid_sql = bool(generated_sql) and not bool(final_state_dict.get("validation_errors"))
    result_hash = None
    gold_hash = None

    actual_action_normalized = normalize_actual_action(actual_action, generated_sql=generated_sql)
    action_correct = actions_match(
        expected_action_normalized, actual_action, generated_sql=generated_sql
    )

    if expected_action_normalized in SQL_POSITIVE_ACTIONS:
        if generated_sql and gold_sql:
            comparison = executor.compare_results(generated_sql, gold_sql)
            execution_correct = bool(comparison.get("match"))
            result_hash = comparison.get("generated_hash")
            gold_hash = comparison.get("gold_hash")
            ok = execution_correct
            partial_credit = _near_miss_partial_credit(
                executor, generated_sql, gold_sql, comparison
            )
        else:
            ok = False
            partial_credit = None
    else:
        ok = action_correct
        partial_credit = None

    for attempt in attempts:
        attempt.setdefault("gold_result_hash", gold_hash)

    error = (
        None
        if ok
        else classify_agent_error(
            expected_action=expected_action_normalized,
            actual_action=actual_action,
            generated_sql=generated_sql,
            gold_sql=gold_sql,
            valid_sql=valid_sql,
            execution_correct=execution_correct,
            final_state=final_state_dict,
        )
    )
    candidate_verification = final_state_dict.get("candidate_verification")
    reliability_decision = final_state_dict.get("reliability_decision")
    graph_reliability_gate_latency_ms = _latency_ms_from_payload(reliability_decision)

    prediction = {
        "actual_action": actual_action,
        "actual_action_normalized": actual_action_normalized,
        "expected_action_normalized": expected_action_normalized,
        "mode": "agent",
        "ok": ok,
        "action_correct": action_correct,
        "execution_correct": execution_correct,
        "partial_credit_semantic": partial_credit,
        "semantic_business_correct": None,
        "valid_sql": valid_sql,
        "normalized_question": final_state_dict.get("normalized_question"),
        "generated_sql": generated_sql,
        "generation_source": final_state_dict.get("generation_source"),
        "gold_sql": gold_sql,
        "explanation": final_state_dict.get("explanation"),
        "intent": final_state_dict.get("intent"),
        "intent_confidence": final_state_dict.get("intent_confidence"),
        "should_generate_sql": final_state_dict.get("should_generate_sql"),
        "safety_label": final_state_dict.get("safety_label"),
        "ambiguity_score": final_state_dict.get("ambiguity_score"),
        "needs_clarification": final_state_dict.get("needs_clarification"),
        "qir": final_state_dict.get("qir"),
        "linked_schema": final_state_dict.get("linked_schema"),
        "value_links": final_state_dict.get("value_links", {}),
        "retrieved_examples": final_state_dict.get("retrieved_examples"),
        "retrieval_diagnostics": final_state_dict.get("retrieval_diagnostics"),
        "exclude_self_retrieval": exclude_self_retrieval,
        "self_overlap_removed": final_state_dict.get("self_overlap_removed", 0),
        "self_overlap_removed_ids": final_state_dict.get("self_overlap_removed_ids", []),
        "retry_count": final_state_dict.get("retry_count"),
        "validation_issues": final_state_dict.get("validation_errors", []),
        "execution_error": final_state_dict.get("execution_error"),
        "execution_passed": final_state_dict.get("execution_result") is not None
        and not final_state_dict.get("execution_error"),
        "max_retries": final_state_dict.get("max_retries"),
        "final_answer": final_state_dict.get("final_answer"),
        "trace_id": final_state_dict.get("trace_id"),
        "latency_ms": latency_ms,
        "result_hash": result_hash,
        "gold_result_hash": gold_hash,
        "attempts": attempts,
        "candidate_sqls": final_state_dict.get("candidate_sqls", []),
        "selected_candidate_id": final_state_dict.get("selected_candidate_id"),
        "candidate_consistency": final_state_dict.get("candidate_consistency"),
        "candidate_verification": candidate_verification,
        "candidate_verification_latency_ms": _latency_ms_from_payload(candidate_verification),
        "multi_candidate_policy": final_state_dict.get("multi_candidate_policy"),
        "multi_candidate_generation_budget": final_state_dict.get(
            "multi_candidate_generation_budget"
        ),
        "multi_candidate_generation_enabled": bool(
            (ablation_config or {}).get("multi_candidate_generation", False)
        ),
        "multi_candidate_adoption_enabled": bool(
            (ablation_config or {}).get("multi_candidate_adoption", False)
        ),
        "multi_candidate_verifier_enabled": bool(
            (ablation_config or {}).get("multi_candidate_verifier", True)
        ),
        "reliability_gate_review_consistency_failures": bool(
            (ablation_config or {}).get("reliability_gate_review_consistency_failures", False)
        ),
        "reliability": final_state_dict.get("reliability"),
        "reliability_decision": reliability_decision,
        "graph_reliability_gate_latency_ms": graph_reliability_gate_latency_ms,
        "error": error,
    }
    if (ablation_config or {}).get("reliability_gate", False):
        consistency_report = analyze_question_sql_consistency(question, generated_sql)
        prediction["sql_consistency_critic"] = consistency_report.as_dict()
        prediction["sql_consistency_issue_count"] = len(consistency_report.issues)
        gate_record = {
            **prediction,
            "should_generate_sql": case.get("should_generate_sql"),
            "intent_confidence": final_state_dict.get("intent_confidence"),
            "execution_result": final_state_dict.get("execution_result"),
            "max_retries": final_state_dict.get("max_retries"),
            "needs_clarification": final_state_dict.get("needs_clarification"),
            "safety_label": final_state_dict.get("safety_label"),
            "sql_consistency_issues": [issue.as_dict() for issue in consistency_report.issues],
        }
        gate_started = time.perf_counter()
        gate_decision = evaluate_reliability_gate(gate_record)
        reliability_gate_latency_ms = int((time.perf_counter() - gate_started) * 1000)
        gate_payload = gate_decision.as_dict()
        gate_payload["latency_ms"] = reliability_gate_latency_ms
        prediction["reliability_gate"] = gate_payload
        prediction["reliability_gate_latency_ms"] = reliability_gate_latency_ms
        prediction["reliability_gate_action"] = gate_decision.action
        prediction["reliability_gate_reason"] = gate_decision.reason
        prediction["reliability_gate_warnings"] = gate_decision.warnings
    return prediction


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


def _metric_value(summary: dict[str, Any], key: str) -> Any:
    metric = summary.get("metrics", {}).get(key, {})
    if isinstance(metric, dict):
        return metric.get("value")
    return None


def print_terminal_summary(
    summary: dict[str, Any], output_dir: Path, failures: list[dict[str, Any]]
) -> None:
    latency = summary.get("latency", {})
    reliability = summary.get("reliability", {})
    unsafe_sql = reliability.get("unsafe_sql") if isinstance(reliability, dict) else None
    reliability_score = reliability.get("score") if isinstance(reliability, dict) else None
    print("\n=== Benchmark Summary ===", flush=True)
    print(
        "evaluated={} failures={}".format(
            summary.get("dataset", {}).get("total_evaluated", 0),
            len(failures),
        ),
        flush=True,
    )
    print(
        "execution_accuracy={} valid_sql_rate={} reliability_score={} unsafe_sql={}".format(
            _metric_value(summary, "execution_accuracy"),
            _metric_value(summary, "valid_sql_rate"),
            reliability_score,
            unsafe_sql,
        ),
        flush=True,
    )
    print(
        "latency_ms mean={} median={} p95={}".format(
            latency.get("mean_ms"),
            latency.get("median_ms"),
            latency.get("p95_ms"),
        ),
        flush=True,
    )
    print(f"artifacts={output_dir}", flush=True)


def flatten_attempts(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    attempts_trace = []
    for record in records:
        case_id = record.get("id") or record.get("case_id")
        for i, attempt in enumerate(record.get("attempts", [])):
            attempts_trace.append(
                {
                    "case_id": case_id,
                    "attempt_index": i,
                    **attempt,
                }
            )
    return attempts_trace


def compact_trace_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    compacted: list[dict[str, Any]] = []
    for record in records:
        item = dict(record)
        attempts = []
        for attempt in item.get("attempts", []):
            compact_attempt = dict(attempt)
            compact_attempt.pop("prompt", None)
            compact_attempt.pop("raw_model_response", None)
            attempts.append(compact_attempt)
        item["attempts"] = attempts
        compacted.append(item)
    return compacted


def records_for_trace_level(
    records: list[dict[str, Any]], trace_level: str
) -> list[dict[str, Any]]:
    if trace_level == "compact":
        return compact_trace_records(records)
    return records


def write_partial_artifacts(
    output_dir: Path, prefix: str, records: list[dict[str, Any]], *, trace_level: str = "full"
) -> None:
    output_records = records_for_trace_level(records, trace_level)
    failures = [
        record
        for record in output_records
        if not (record.get("ok") or record.get("execution_correct") or record.get("result_match"))
    ]
    attempts = flatten_attempts(output_records)
    validate_benchmark_trace_contract(output_records, attempts, default_ablation_id="partial")
    write_jsonl(output_dir / f"{prefix}_partial_predictions.jsonl", output_records)
    write_jsonl(output_dir / f"{prefix}_partial_failures.jsonl", failures)
    write_jsonl(output_dir / f"{prefix}_partial_attempts.jsonl", attempts)


def build_output_dir(config_id: str, stamp: str, output_dir: str | None = None) -> Path:
    if output_dir:
        return Path(output_dir)
    return RESULTS_DIR / "benchmark" / f"{stamp}_{slug(config_id)}"


def get_model_slug() -> str:
    if SETTINGS.default_model_path:
        return slug(Path(SETTINGS.default_model_path).stem)
    return "qwen2-5-coder-7b"


def get_model_path() -> str | None:
    if SETTINGS.default_model_path:
        return SETTINGS.default_model_path
    return str(MODELS_DIR / "generation" / "qwen2.5-coder-7b-instruct-q4_k_m.gguf")


def get_model_name() -> str:
    return Path(get_model_path() or "qwen2.5-coder-7b-default").stem


def split_module_flags(flags: dict[str, Any]) -> tuple[list[str], list[str]]:
    enabled = sorted(k for k, v in flags.items() if isinstance(v, bool) and v)
    disabled = sorted(k for k, v in flags.items() if isinstance(v, bool) and not v)
    return enabled, disabled


def run(args: argparse.Namespace) -> Path:
    started_at = utc_now()
    dataset = load_named_dataset(args.dataset, args.path)
    trace_level = getattr(args, "trace_level", "full")
    exclude_self = bool(getattr(args, "exclude_self", False))
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
        "multi_candidate_generation": True,
        "multi_candidate_adoption": True,
        "multi_candidate_verifier": True,
        "deterministic_templates": False,
        "reliability_gate": False,
        "llm_judge": False,
    }
    if getattr(args, "use_judge", False):
        ablation_config = dict(ablation_config)
        ablation_config["llm_judge"] = True
    if args.mode == "agent":
        ablation_config = apply_agent_retrieval_overrides(
            ablation_config,
            retrieval_backend=getattr(args, "retrieval_backend", None),
            reranker_name=getattr(args, "reranker", None),
        )
    ablation_contract = ablation_runtime_contract(ablation_config)
    enabled_modules, disabled_modules = split_module_flags(ablation_config)
    max_retries_override = getattr(args, "max_retries_override", None)

    config_id = args.config_id or f"{args.mode}_{args.dataset}_{model_slug}_{ablation_id}"
    output_dir = build_output_dir(config_id, stamp, args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    prefix = f"{stamp}_{model_slug}_{ablation_id}"

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
        retrieval_backend_arg = getattr(args, "retrieval_backend", None)
        retrieval_backend_mode = retrieval_backend_arg or ("hybrid" if args.use_vector else "bm25")
        requested_reranker = getattr(args, "reranker", None)
        if retrieval_backend_mode == "hybrid_rerank" and not requested_reranker:
            requested_reranker = "identity"
        use_reranker = bool(requested_reranker and requested_reranker != "none")
        retriever_mode = (
            "hybrid" if retrieval_backend_mode == "hybrid_rerank" else retrieval_backend_mode
        )
        retriever = HybridRetriever(retrieval_mode=retriever_mode)
        active_reranker_obj = None
        if use_reranker:
            candidate_reranker = create_reranker(requested_reranker)
            if isinstance(candidate_reranker, CrossEncoderReranker):
                active_reranker_obj = candidate_reranker
        for index, case in enumerate(cases, start=1):
            record = dict(
                case,
                **retrieval_prediction(
                    case,
                    retriever,
                    top_k=args.top_k,
                    exclude_self=exclude_self,
                    use_reranker=use_reranker,
                    reranker_name=requested_reranker,
                    reranker_obj=active_reranker_obj,
                ),
            )
            records.append(record)
            log_progress(index, case, record)
            write_partial_artifacts(output_dir, prefix, records, trace_level=trace_level)
    elif args.mode == "gold":
        executor = ReadOnlyExecutor()
        for index, case in enumerate(cases, start=1):
            started = time.perf_counter()
            record = dict(case, **gold_prediction(case, executor))
            record.setdefault("latency_ms", int((time.perf_counter() - started) * 1000))
            records.append(record)
            log_progress(index, case, record)
            write_partial_artifacts(output_dir, prefix, records, trace_level=trace_level)
    elif args.mode == "agent":
        from src.graph.workflow import create_workflow

        checkpoint_db = getattr(args, "checkpoint_db", None)
        if checkpoint_db:
            from src.graph.checkpoints import build_checkpointer

            workflow = create_workflow(checkpointer=build_checkpointer(checkpoint_db))
        else:
            workflow = create_workflow()
        executor = ReadOnlyExecutor()
        for index, case in enumerate(cases, start=1):
            case_started = time.perf_counter()
            try:
                prediction = agent_prediction(
                    case,
                    workflow,
                    executor,
                    ablation_config=ablation_config,
                    exclude_self_retrieval=exclude_self,
                    top_k=args.top_k,
                    max_retries_override=max_retries_override,
                )
            except Exception as exc:
                prediction = exception_prediction(
                    case,
                    exc,
                    latency_ms=int((time.perf_counter() - case_started) * 1000),
                    exclude_self_retrieval=exclude_self,
                )
            record = dict(case, **prediction)
            records.append(record)
            log_progress(index, case, record)
            write_partial_artifacts(output_dir, prefix, records, trace_level=trace_level)
    else:  # pragma: no cover - argparse enforces choices.
        raise ValueError(f"Unsupported mode: {args.mode}")

    failures = [
        record
        for record in records
        if not (record.get("ok") or record.get("execution_correct") or record.get("result_match"))
    ]
    dataset_summary = summarize_cases(cases)
    difficulty_counts = dataset_summary.get("by_difficulty", {})
    self_overlap_removed_total = sum(
        int(record.get("self_overlap_removed") or 0) for record in records
    )
    retrieval_backend = getattr(args, "retrieval_backend", None) or (
        "hybrid" if args.use_vector else "bm25"
    )
    requested_reranker = getattr(args, "reranker", None)
    effective_reranker = requested_reranker or (
        "identity" if retrieval_backend == "hybrid_rerank" else None
    )
    config = {
        "config_id": config_id,
        "mode": args.mode,
        "dataset": args.dataset,
        "dataset_path": str(dataset.path),
        "sample": args.sample or len(cases),
        "samples_per_level": args.samples_per_level,
        "selection_policy": selection_policy,
        "difficulty_counts": difficulty_counts,
        "dataset_hash": sha256_file(Path(dataset.path)),
        "selected_cases_hash": sha256_jsonable(cases),
        "top_k": args.top_k,
        "use_vector": args.use_vector,
        "retrieval_backend": retrieval_backend,
        "retrieval_reranker": effective_reranker if effective_reranker != "none" else None,
        "retrieval_reranker_backend": resolve_reranker_backend(
            effective_reranker if effective_reranker else None
        ),
        "retrieval_reranker_warning": (
            "model_backed_reranker_not_implemented_identity_placeholder_used"
            if resolve_reranker_backend(effective_reranker) == "identity"
            and effective_reranker not in {None, "none", "identity"}
            else None
        ),
        "max_retries": (
            SETTINGS.max_retries if max_retries_override is None else max_retries_override
        ),
        "max_retries_source": "settings" if max_retries_override is None else "config",
        "llm_context_window": SETTINGS.llm_context_window,
        "prompt_template": {
            "generation": "src/generation/prompts/sql_generation.j2",
            "repair": "src/generation/prompts/sql_repair.j2",
        },
        "trace_level": trace_level,
        "exclude_self": exclude_self,
        "retrieval_self_overlap_policy": {
            "enabled": exclude_self,
            "match_on": ["base_id", "normalized_question"],
            "ignored_id_prefixes": ["fs_", "idx_"],
            "removed_total": self_overlap_removed_total,
        },
        "model_name": model_name,
        "model_path": model_path,
        "model_slug": model_slug,
        "ablation_id": ablation_id,
        "enabled_modules": enabled_modules,
        "disabled_modules": disabled_modules,
        "module_flags": ablation_config,
        "ablation_runtime_contract": ablation_contract,
        "judge": {
            "enabled": bool(getattr(args, "use_judge", False)),
            "provider": getattr(args, "judge_provider", "mock"),
            "sample_size": getattr(args, "judge_sample_size", None),
            "failures_only": bool(getattr(args, "judge_failures_only", True)),
        },
        "started_at": started_at,
        "finished_at": utc_now(),
        "git_commit": git_commit(),
    }
    checkpoint_db = getattr(args, "checkpoint_db", None)
    if checkpoint_db:
        config["checkpoint_db"] = checkpoint_db
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
        summary["retrieval_self_overlap"] = {
            "enabled": exclude_self,
            "removed_total": self_overlap_removed_total,
        }
    else:
        summary["metrics"] = add_bootstrap_cis(
            aggregate_basic_metrics(records),
            records,
            iterations=args.bootstrap_iterations,
            seed=args.seed,
        )
        credit_values = [
            r.get("partial_credit_semantic")
            for r in records
            if isinstance(r.get("partial_credit_semantic"), (int, float))
        ]
        if credit_values:
            summary["metrics"]["partial_credit_semantic_mean"] = round(
                sum(credit_values) / len(credit_values), 4
            )
            summary["metrics"]["partial_credit_semantic_coverage"] = len(credit_values)
        summary["reliability"] = reliability_score(records).as_dict()
        summary["retrieval_self_overlap"] = {
            "enabled": exclude_self,
            "removed_total": self_overlap_removed_total,
        }

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
        "manifest": output_dir / f"{prefix}_artifact_manifest.json",
    }
    if args.mode == "retrieval":
        artifact_paths["retrieval_metrics"] = output_dir / f"{prefix}_retrieval_metrics.json"

    summary["artifacts"] = {key: str(path) for key, path in artifact_paths.items()}

    output_records = records_for_trace_level(records, trace_level)
    output_failures = [
        record
        for record in output_records
        if not (record.get("ok") or record.get("execution_correct") or record.get("result_match"))
    ]
    output_attempts = flatten_attempts(output_records) if args.mode == "agent" else []
    trace_contract_summary = validate_benchmark_trace_contract(
        output_records,
        output_attempts,
        default_ablation_id=ablation_id,
    )
    summary["trace_contract"] = {
        **trace_contract_summary,
        "validated": True,
    }

    write_json(artifact_paths["config"], config)
    write_jsonl(artifact_paths["predictions"], output_records)
    write_jsonl(artifact_paths["failures"], output_failures)

    # Write attempts trace for agent mode
    write_jsonl(artifact_paths["attempts"], output_attempts)

    write_json(artifact_paths["summary_json"], summary)
    if args.mode == "retrieval":
        write_json(artifact_paths["retrieval_metrics"], summary["retrieval_metrics"])

    if getattr(args, "use_judge", False):
        judge_paths = judge_benchmark_artifact(
            output_dir,
            output_dir=output_dir,
            provider_name=getattr(args, "judge_provider", "mock"),
            judge_model=getattr(args, "judge_model", None),
            reasoning_enabled=getattr(args, "judge_reasoning", None),
            failures_only=bool(getattr(args, "judge_failures_only", True)),
            sample_size=getattr(args, "judge_sample_size", None),
        )
        artifact_paths.update(
            {
                "judgments": judge_paths["judgments"],
                "judge_summary": judge_paths["summary"],
                "judge_costs": judge_paths["costs"],
                "semantic_business_summary_csv": judge_paths["semantic_summary"],
                "judge_reasoning": judge_paths["reasoning"],
            }
        )
        summary["artifacts"] = {key: str(path) for key, path in artifact_paths.items()}
        summary["judge"] = {
            "enabled": True,
            "provider": getattr(args, "judge_provider", "mock"),
            "model": getattr(args, "judge_model", None),
            "reasoning_enabled": getattr(args, "judge_reasoning", None),
            "sample_size": getattr(args, "judge_sample_size", None),
            "failures_only": bool(getattr(args, "judge_failures_only", True)),
            "artifacts": {key: str(path) for key, path in judge_paths.items()},
            "authoritative": False,
        }
        write_json(artifact_paths["summary_json"], summary)

    # Export CSVs and Paper Tables
    export_benchmark_csvs(records, summary, output_dir, prefix=prefix)
    generate_paper_tables(summary, artifact_paths["paper_tables_md"])

    write_benchmark_markdown_report(summary, artifact_paths["summary_md"])
    write_json(
        artifact_paths["manifest"],
        build_artifact_manifest(output_dir, summary, artifact_paths),
    )
    print_terminal_summary(summary, output_dir, failures)
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
    parser.add_argument(
        "--samples-per-level", type=int, help="Evaluate N cases from each difficulty level."
    )
    parser.add_argument(
        "--top-k", type=int, default=5, help="Number of examples to retrieve (default: 5)."
    )
    parser.add_argument(
        "--use-vector", action="store_true", help="Enable vector fallback store in retrieval mode."
    )
    parser.add_argument(
        "--retrieval-backend",
        choices=("bm25", "vector", "hybrid", "hybrid_rerank"),
        default=None,
        help="Retrieval backend for retrieval-mode ablations. hybrid_rerank uses the current identity reranker.",
    )
    parser.add_argument(
        "--reranker",
        choices=("none", "identity", "bge-reranker-base", "bge-reranker-v2-m3"),
        default=None,
        help=(
            "Optional retrieval reranker. Current runtime has an identity placeholder; "
            "model-backed choices are recorded with a warning until implemented."
        ),
    )
    parser.add_argument(
        "--exclude-self",
        action="store_true",
        help="Remove retrieved examples that match the evaluated case by base id or normalized question.",
    )
    parser.add_argument(
        "--checkpoint-db",
        default=None,
        help="Agent mode only: path to a SQLite checkpoint database for LangGraph state persistence.",
    )
    parser.add_argument(
        "--trace-level",
        choices=("full", "compact"),
        default="full",
        help="Use full prompt/raw-response trace or compact artifacts without large prompt/raw fields.",
    )
    parser.add_argument("--config-id", help="Stable identifier used in the output directory name.")
    parser.add_argument(
        "--ablation-id", help="Ablation identifier included in output names and summaries."
    )
    parser.add_argument("--output-dir", help="Explicit artifact directory.")
    parser.add_argument("--config", help="Path to a benchmark YAML config file.")
    parser.add_argument(
        "--seed",
        type=int,
        default=SETTINGS.random_seed,
        help="Random seed for deterministic metric resampling.",
    )
    parser.add_argument(
        "--bootstrap-iterations",
        type=int,
        default=1000,
        help="Bootstrap iterations for confidence intervals.",
    )
    parser.add_argument(
        "--use-judge",
        action="store_true",
        help="Generate judgment artifacts after the benchmark run.",
    )
    parser.add_argument(
        "--judge-provider",
        choices=("mock", "openrouter"),
        default="mock",
        help="Judge provider. openrouter requires OPENROUTER_API_KEY.",
    )
    parser.add_argument(
        "--judge-sample-size", type=int, help="Limit selected predictions sent to the judge."
    )
    parser.add_argument(
        "--judge-model",
        help="Judge model id. For OpenRouter, use ids such as qwen/qwen3.6-plus.",
    )
    parser.add_argument(
        "--judge-reasoning",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Enable provider reasoning mode when supported. Use --no-judge-reasoning to force it off.",
    )
    parser.add_argument(
        "--judge-failures-only",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Judge failures only by default. Use --no-judge-failures-only to judge all predictions.",
    )
    parser.set_defaults(ablation_config=None)
    return parser


def load_config_yaml(path: str) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def parse_max_retries_override(features: dict[str, Any] | None) -> int | None:
    if not features or "max_retries" not in features:
        return None
    value = features["max_retries"]
    if isinstance(value, bool):
        raise ValueError("features.max_retries must be a non-negative integer, not a boolean.")
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("features.max_retries must be a non-negative integer.") from exc
    if parsed < 0:
        raise ValueError("features.max_retries must be a non-negative integer.")
    return parsed


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
                if "split" in ds:
                    args.dataset = ds["split"]
                if "source" in ds:
                    args.path = ds["source"]
                if "sample_size" in ds:
                    args.sample = ds["sample_size"]
        if "features" in yaml_data:
            feat = yaml_data["features"]
            args.ablation_config = normalize_feature_flags(feat)
            args.max_retries_override = parse_max_retries_override(feat)
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
        if "trace_level" in yaml_data:
            args.trace_level = yaml_data["trace_level"]
        if "exclude_self" in yaml_data:
            args.exclude_self = bool(yaml_data["exclude_self"])
        if "retrieval" in yaml_data and isinstance(yaml_data["retrieval"], dict):
            retrieval = yaml_data["retrieval"]
            if "top_k" in retrieval:
                args.top_k = int(retrieval["top_k"])
            if "backend" in retrieval:
                args.retrieval_backend = str(retrieval["backend"])
                args.use_vector = args.retrieval_backend in {"vector", "hybrid", "hybrid_rerank"}
            if "reranker" in retrieval:
                args.reranker = str(retrieval["reranker"])

    if args.sample == 0:
        args.sample = None
    output_dir = run(args)
    print(f"Benchmark artifacts written to: {output_dir}")


if __name__ == "__main__":
    main()
