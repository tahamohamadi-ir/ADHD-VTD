from __future__ import annotations

from pathlib import Path
from typing import Any

from src.evaluation.phase0_audit import build_phase0_summary

try:
    from src.config.paths import QUESTION_AUDIT_DIR
except Exception:  # pragma: no cover
    QUESTION_AUDIT_DIR = Path("data/questions/audit")


def _metric_row(name: str, metric: dict[str, Any]) -> str:
    value = metric.get("value")
    if isinstance(value, float):
        rendered = f"{value:.4f}"
    else:
        rendered = str(value)
    return f"| `{name}` | {rendered} | {metric.get('numerator', '')} | {metric.get('denominator', '')} | {metric.get('description', '')} |"


def generate_phase0_markdown_report(summary: dict[str, Any] | None = None) -> str:
    s = summary or build_phase0_summary()
    lines: list[str] = []
    lines.append("# Phase 0 Evaluation Summary")
    lines.append("")
    lines.append("## Dataset")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---:|")
    lines.append(f"| Total cases | {s['cases']['total']} |")
    lines.append(f"| SQL-positive | {s['cases']['sql_positive']} |")
    lines.append(f"| Behavioral / non-SQL | {s['cases']['non_sql_or_behavioral']} |")
    lines.append("")
    lines.append("## Gold SQL Execution")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---:|")
    lines.append(f"| Execution result rows | {s['execution_results_count']} |")
    lines.append(f"| Successful | {s['gold_sql_executed_successfully']} |")
    lines.append(f"| Failed | {s['gold_sql_failed']} |")
    lines.append("")
    lines.append("## Metrics")
    lines.append("")
    lines.append("| Metric | Value | Numerator | Denominator | Description |")
    lines.append("|---|---:|---:|---:|---|")
    for name, metric in s.get("metrics", {}).items():
        lines.append(_metric_row(name, metric))
    lines.append("")
    lines.append("## Reliability Score")
    lines.append("")
    rel = s.get("reliability", {})
    lines.append("| Field | Value |")
    lines.append("|---|---:|")
    for key, value in rel.items():
        lines.append(f"| `{key}` | {value} |")
    lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    lines.append("This report is Phase-0/Phase-1 oriented. It validates dataset executability and evaluation infrastructure before full LLM benchmarking, CAG, LangGraph, or reflexion.")
    lines.append("")
    return "\n".join(lines)


def write_phase0_markdown_report(path: str | Path | None = None) -> Path:
    out = Path(path) if path else QUESTION_AUDIT_DIR / "phase0_evaluation_summary.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(generate_phase0_markdown_report(), encoding="utf-8")
    return out


def _value_cell(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.4f}"
    if value is None:
        return ""
    return str(value)


def _count_table(title: str, values: dict[str, Any]) -> list[str]:
    lines = [f"## {title}", "", "| Key | Count |", "|---|---:|"]
    if not values:
        lines.append("| none | 0 |")
    else:
        for key, value in values.items():
            lines.append(f"| `{key}` | {value} |")
    lines.append("")
    return lines


def generate_benchmark_markdown_report(summary: dict[str, Any]) -> str:
    """Render a benchmark summary artifact.

    The report is intentionally mode-aware but model-agnostic. It can describe
    gold-SQL plumbing runs, retrieval-only runs, and later full agent runs with
    the same artifact shape.
    """
    config = summary.get("config", {})
    dataset = summary.get("dataset", {})
    metrics = summary.get("metrics", {})
    reliability = summary.get("reliability", {})
    retrieval = summary.get("retrieval_metrics")
    errors = summary.get("error_analysis", {})
    artifacts = summary.get("artifacts", {})

    lines: list[str] = []
    lines.append("# Benchmark Summary")
    lines.append("")
    lines.append("## Run")
    lines.append("")
    lines.append("| Field | Value |")
    lines.append("|---|---|")
    for key in ("config_id", "mode", "dataset", "sample", "top_k", "use_vector", "started_at", "finished_at"):
        if key in config:
            lines.append(f"| `{key}` | {_value_cell(config.get(key))} |")
    lines.append("")

    lines.append("## Dataset")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---:|")
    for key in ("path", "total_loaded", "total_evaluated", "sql_positive", "non_sql_or_behavioral"):
        if key in dataset:
            lines.append(f"| `{key}` | {_value_cell(dataset.get(key))} |")
    lines.append("")

    if metrics:
        lines.append("## Core Metrics")
        lines.append("")
        lines.append("| Metric | Value | Numerator | Denominator |")
        lines.append("|---|---:|---:|---:|")
        for name, metric in metrics.items():
            lines.append(
                f"| `{name}` | {_value_cell(metric.get('value'))} | "
                f"{_value_cell(metric.get('numerator'))} | {_value_cell(metric.get('denominator'))} |"
            )
        lines.append("")

    if reliability:
        lines.append("## Reliability")
        lines.append("")
        lines.append("| Field | Value |")
        lines.append("|---|---:|")
        for key, value in reliability.items():
            lines.append(f"| `{key}` | {_value_cell(value)} |")
        lines.append("")

    if retrieval:
        lines.append("## Retrieval Metrics")
        lines.append("")
        lines.append("| Metric | Value |")
        lines.append("|---|---:|")
        for key, value in retrieval.items():
            lines.append(f"| `{key}` | {_value_cell(value)} |")
        lines.append("")

    lines.extend(_count_table("Errors By Type", errors.get("by_error", {})))
    lines.extend(_count_table("Errors By Difficulty", errors.get("by_difficulty", {})))
    lines.extend(_count_table("Errors By Category", errors.get("by_category", {})))

    examples = errors.get("examples", [])
    if examples:
        lines.append("## Failure Examples")
        lines.append("")
        lines.append("| ID | Error | Question |")
        lines.append("|---|---|---|")
        for item in examples[:10]:
            question = str(item.get("question") or "").replace("\n", " ")
            lines.append(f"| `{item.get('id')}` | `{item.get('error')}` | {question} |")
        lines.append("")

    if artifacts:
        lines.append("## Artifacts")
        lines.append("")
        lines.append("| Artifact | Path |")
        lines.append("|---|---|")
        for key, value in artifacts.items():
            lines.append(f"| `{key}` | `{value}` |")
        lines.append("")

    lines.append("## Notes")
    lines.append("")
    lines.append(
        "Retrieval-only runs measure whether the evidence bank returns useful examples; "
        "they are not end-to-end SQL generation benchmarks."
    )
    lines.append("")
    return "\n".join(lines)


def write_benchmark_markdown_report(summary: dict[str, Any], path: str | Path) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(generate_benchmark_markdown_report(summary), encoding="utf-8")
    return out


if __name__ == "__main__":
    out = write_phase0_markdown_report()
    print(f"Report written to: {out}")
