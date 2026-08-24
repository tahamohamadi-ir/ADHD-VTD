from __future__ import annotations

from _bootstrap_path import PROJECT_ROOT

from src.evaluation.dataset_loader import load_phase0_50q_cases, summarize_cases
from src.evaluation.gold_sql_runner import run_gold_cases
from src.evaluation.metrics import aggregate_basic_metrics
from src.evaluation.reliability_metrics import reliability_score
from src.evaluation.report_generator import write_phase0_markdown_report
from src.evaluation.phase0_audit import write_phase0_summary_json


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    print(f"PROJECT_ROOT={PROJECT_ROOT}")

    ds = load_phase0_50q_cases()
    summary = summarize_cases(ds.cases)
    print("Dataset summary:", summary)
    assert_true(ds.total == 50, "Phase0 50Q dataset should contain 50 cases.")
    assert_true(summary["sql_positive"] == 50, "Phase0 50Q should be SQL-positive.")

    rows = run_gold_cases()
    ok = sum(1 for r in rows if r.get("ok"))
    print(f"Gold SQL ok: {ok}/{len(rows)}")
    assert_true(len(rows) == 50, "Gold SQL runner should produce 50 rows.")
    assert_true(ok == 50, "All Phase0 gold SQL cases should execute successfully.")

    metrics = aggregate_basic_metrics(rows)
    print("Metrics:", metrics)
    assert_true(metrics["execution_accuracy"]["value"] == 1.0, "Gold identity execution accuracy should be 1.0.")

    rs = reliability_score(rows)
    print("Reliability:", rs.as_dict())
    assert_true(rs.total_cases == 50, "Reliability should evaluate 50 cases.")

    json_out = write_phase0_summary_json()
    md_out = write_phase0_markdown_report()
    print(f"JSON summary: {json_out}")
    print(f"Markdown report: {md_out}")

    print("Evaluation foundation checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
