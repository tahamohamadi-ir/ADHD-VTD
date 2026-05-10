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


if __name__ == "__main__":
    out = write_phase0_markdown_report()
    print(f"Report written to: {out}")
