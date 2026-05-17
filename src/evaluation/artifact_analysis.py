from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from src.config.paths import RESULTS_DIR
from src.evaluation.dataset_loader import read_json, read_jsonl, write_json, write_jsonl


REQUIRED_SUFFIXES = {
    "summary": "_summary.json",
    "predictions": "_predictions.jsonl",
    "attempts": "_attempts.jsonl",
    "failures": "_failures.jsonl",
}


@dataclass(frozen=True, slots=True)
class BenchmarkArtifact:
    root: Path
    summary_path: Path
    predictions_path: Path
    attempts_path: Path
    failures_path: Path


def _find_one(root: Path, suffix: str) -> Path:
    matches = sorted(root.glob(f"*{suffix}"))
    if not matches:
        raise FileNotFoundError(f"Missing required artifact '*{suffix}' in {root}")
    return matches[0]


def locate_benchmark_artifact(path: str | Path) -> BenchmarkArtifact:
    root = Path(path)
    if not root.exists() or not root.is_dir():
        raise FileNotFoundError(f"Benchmark artifact directory does not exist: {root}")
    return BenchmarkArtifact(
        root=root,
        summary_path=_find_one(root, REQUIRED_SUFFIXES["summary"]),
        predictions_path=_find_one(root, REQUIRED_SUFFIXES["predictions"]),
        attempts_path=_find_one(root, REQUIRED_SUFFIXES["attempts"]),
        failures_path=_find_one(root, REQUIRED_SUFFIXES["failures"]),
    )


def _validation_codes(record: dict[str, Any]) -> list[str]:
    codes: list[str] = []
    for issue in record.get("validation_issues") or []:
        if isinstance(issue, dict):
            code = issue.get("code") or issue.get("type")
            if code:
                codes.append(str(code))
        else:
            text = str(issue)
            marker = "code='"
            if marker in text:
                codes.append(text.split(marker, 1)[1].split("'", 1)[0])
    for attempt in record.get("attempts") or []:
        if not isinstance(attempt, dict):
            continue
        for issue in attempt.get("validation_errors") or []:
            text = str(issue)
            marker = "code='"
            if marker in text:
                codes.append(text.split(marker, 1)[1].split("'", 1)[0])
    return sorted(set(codes))


def classify_research_error(record: dict[str, Any]) -> str:
    error = str(record.get("error") or "")
    intent = str(record.get("intent") or "")
    expected_action = str(record.get("expected_action") or "")
    actual_action = str(record.get("actual_action") or "")
    codes = _validation_codes(record)

    if intent == "unsafe_query" and expected_action == "generate_sql":
        return "SAFETY_FALSE_POSITIVE"
    if actual_action.startswith("ask_") and expected_action == "generate_sql":
        return "FALSE_ABSTENTION"
    if any(code.startswith("ANALYTICAL_SHAPE") for code in codes):
        return "SHAPE_CONTRACT_ERROR"
    if error == "INVALID_SQL":
        return "INVALID_SQL"
    if error == "RESULT_MISMATCH":
        if record.get("valid_sql") and record.get("semantic_business_correct") is None:
            return "SEMANTIC_REVIEW_REQUIRED"
        return "RESULT_MISMATCH"
    if error == "MISSING_GENERATED_SQL":
        return "FALSE_ABSTENTION"
    if error == "ACTION_MISMATCH":
        return "INTENT_ERROR"
    return error or "UNKNOWN_ERROR"


def _is_failure(record: dict[str, Any]) -> bool:
    return not bool(record.get("ok") or record.get("execution_correct") or record.get("result_match"))


def build_error_rows(predictions: list[dict[str, Any]], *, max_examples: int = 20) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record in predictions:
        if not _is_failure(record):
            continue
        rows.append(
            {
                "id": record.get("id") or record.get("case_id"),
                "difficulty": record.get("difficulty"),
                "category": record.get("category"),
                "intent": record.get("intent"),
                "expected_action": record.get("expected_action"),
                "actual_action": record.get("actual_action"),
                "benchmark_error": record.get("error"),
                "research_error": classify_research_error(record),
                "valid_sql": record.get("valid_sql"),
                "execution_correct": record.get("execution_correct"),
                "semantic_business_correct": record.get("semantic_business_correct"),
                "validation_codes": _validation_codes(record),
                "question": record.get("question_fa") or record.get("question"),
                "generated_sql": record.get("generated_sql"),
                "gold_sql": record.get("gold_sql"),
            }
        )
        if len(rows) >= max_examples:
            break
    return rows


def _metric_line(name: str, metric: dict[str, Any]) -> str:
    value = metric.get("value")
    numerator = metric.get("numerator")
    denominator = metric.get("denominator")
    ci = metric.get("ci95")
    ci_text = ""
    if isinstance(ci, dict):
        ci_text = f" [{ci.get('lower')}, {ci.get('upper')}]"
    return f"| {name} | {value}{ci_text} | {numerator} | {denominator} |"


def render_error_report(
    *,
    artifact: BenchmarkArtifact,
    summary: dict[str, Any],
    predictions: list[dict[str, Any]],
    attempts: list[dict[str, Any]],
    error_rows: list[dict[str, Any]],
) -> str:
    config = summary.get("config", {})
    metrics = summary.get("metrics", {})
    reliability = summary.get("reliability", {})
    latency = summary.get("latency", {})
    dataset = summary.get("dataset", {})
    taxonomy = Counter(row["research_error"] for row in error_rows)
    by_difficulty = Counter(str(row.get("difficulty") or "unknown") for row in error_rows)
    by_category = Counter(str(row.get("category") or "unknown") for row in error_rows)
    semantic_unknown = sum(1 for row in predictions if row.get("semantic_business_correct") is None)

    lines = [
        "# Phase 11 Artifact-Backed Error Analysis",
        "",
        f"Generated at: {datetime.now().isoformat(timespec='seconds')}",
        "",
        "## Source Artifact",
        "",
        f"- artifact_dir: `{artifact.root}`",
        f"- summary: `{artifact.summary_path.name}`",
        f"- predictions: `{artifact.predictions_path.name}`",
        f"- attempts: `{artifact.attempts_path.name}`",
        f"- failures: `{artifact.failures_path.name}`",
        "",
        "## Anti-Fake / Anti-Overfit Statement",
        "",
        "This report is generated only from existing benchmark artifacts. It does not run a model, edit predictions, infer missing labels, or create semantic judge outcomes.",
        "",
        "## Run Metadata",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| model_name | {config.get('model_name')} |",
        f"| model_path | {config.get('model_path')} |",
        f"| model_slug | {config.get('model_slug')} |",
        f"| ablation_id | {config.get('ablation_id')} |",
        f"| enabled_modules | {config.get('enabled_modules')} |",
        f"| disabled_modules | {config.get('disabled_modules')} |",
        f"| dataset_hash | {config.get('dataset_hash')} |",
        f"| selected_cases_hash | {config.get('selected_cases_hash')} |",
        f"| git_commit | {config.get('git_commit')} |",
        "",
        "## Dataset",
        "",
        "| Field | Value |",
        "|---|---:|",
        f"| total_loaded | {dataset.get('total_loaded')} |",
        f"| total_evaluated | {dataset.get('total_evaluated')} |",
        f"| sql_positive | {dataset.get('sql_positive')} |",
        f"| non_sql_or_behavioral | {dataset.get('non_sql_or_behavioral')} |",
        "",
        "## Metrics",
        "",
        "| Metric | Value | Numerator | Denominator |",
        "|---|---:|---:|---:|",
    ]
    for name, metric in metrics.items():
        if isinstance(metric, dict):
            lines.append(_metric_line(name, metric))
    lines.extend(
        [
            "",
            "## Reliability",
            "",
            "| Field | Value |",
            "|---|---:|",
        ]
    )
    for key, value in reliability.items():
        lines.append(f"| {key} | {value} |")
    lines.extend(
        [
            "",
            "## Latency",
            "",
            "| Field | Value |",
            "|---|---:|",
        ]
    )
    for key, value in latency.items():
        lines.append(f"| {key} | {value} |")
    lines.extend(
        [
            "",
            "## Research Error Taxonomy",
            "",
            "| Error | Count |",
            "|---|---:|",
        ]
    )
    for key, count in taxonomy.most_common():
        lines.append(f"| {key} | {count} |")
    lines.extend(
        [
            "",
            "## Failure Distribution",
            "",
            "### By Difficulty",
            "",
            "| Difficulty | Count |",
            "|---|---:|",
        ]
    )
    for key, count in by_difficulty.most_common():
        lines.append(f"| {key} | {count} |")
    lines.extend(["", "### By Category", "", "| Category | Count |", "|---|---:|"])
    for key, count in by_category.most_common():
        lines.append(f"| {key} | {count} |")
    lines.extend(
        [
            "",
            "## Representative Failures",
            "",
            "| ID | Difficulty | Category | Benchmark Error | Research Error | Valid SQL |",
            "|---|---|---|---|---|---:|",
        ]
    )
    for row in error_rows:
        lines.append(
            "| {id} | {difficulty} | {category} | {benchmark_error} | {research_error} | {valid_sql} |".format(
                **row
            )
        )
    lines.extend(
        [
            "",
            "## Trace Completeness",
            "",
            f"- predictions: {len(predictions)}",
            f"- attempts: {len(attempts)}",
            f"- representative_failures: {len(error_rows)}",
            "",
            "## Semantic Business Correctness Gap",
            "",
            f"- semantic_business_correct is missing/null for {semantic_unknown} predictions.",
            "- This is expected before Phase 16. Do not report semantic correctness from this artifact.",
            "",
            "## Limitations",
            "",
            "- This is a small smoke artifact unless the source run says otherwise.",
            "- Error labels are report-side taxonomy labels and do not replace benchmark outcomes.",
            "- Low EX/reliability is a model/system quality finding, not a reason to edit benchmark data.",
        ]
    )
    return "\n".join(lines) + "\n"


def analyze_benchmark_artifact(
    artifact_dir: str | Path,
    *,
    output_dir: str | Path | None = None,
    max_examples: int = 20,
) -> dict[str, Path]:
    artifact = locate_benchmark_artifact(artifact_dir)
    summary = read_json(artifact.summary_path)
    predictions = read_jsonl(artifact.predictions_path)
    attempts = read_jsonl(artifact.attempts_path)
    _ = read_jsonl(artifact.failures_path)
    error_rows = build_error_rows(predictions, max_examples=max_examples)

    if output_dir is None:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_root = RESULTS_DIR / "error_analysis" / f"{stamp}_phase11_{artifact.root.name}"
    else:
        output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    report = render_error_report(
        artifact=artifact,
        summary=summary,
        predictions=predictions,
        attempts=attempts,
        error_rows=error_rows,
    )
    report_path = output_root / "error_report.md"
    cases_path = output_root / "failure_cases.jsonl"
    summary_path = output_root / "analysis_summary.json"

    report_path.write_text(report, encoding="utf-8")
    write_jsonl(cases_path, error_rows)
    write_json(
        summary_path,
        {
            "source_artifact": str(artifact.root),
            "report": str(report_path),
            "failure_cases": str(cases_path),
            "total_predictions": len(predictions),
            "total_attempts": len(attempts),
            "total_failures_analyzed": len(error_rows),
            "research_error_counts": dict(Counter(row["research_error"] for row in error_rows).most_common()),
        },
    )
    return {"report": report_path, "failure_cases": cases_path, "summary": summary_path}
