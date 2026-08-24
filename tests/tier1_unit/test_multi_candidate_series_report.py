from __future__ import annotations

from src.evaluation.dataset_loader import read_json, read_jsonl, write_json
from src.evaluation.multi_candidate_series_report import build_multi_candidate_series_report


def _write_comparison(root, *, status: str, ex_delta: float, valid_delta: float, p95_delta: float):
    root.mkdir()
    write_json(
        root / "multi_candidate_ablation_summary.json",
        {
            "metric_deltas": {
                "execution_accuracy": ex_delta,
                "valid_sql_rate": valid_delta,
                "reliability_score": 0.0,
                "unsafe_sql": 0.0,
                "latency_p95_ms": p95_delta,
            },
            "multi_candidate_activation": {
                "activation_rate": 0.5,
                "generated_candidate_count_distribution": {"2": 1, "0": 3},
            },
            "candidate_issue_counts": {"NO_VIABLE_CANDIDATES": 1},
            "same_selected_cases_hash": True,
            "acceptance_checks": {
                "status": status,
                "semantic_evidence_available": False,
            },
        },
    )


def test_multi_candidate_series_report_preserves_negative_findings(tmp_path):
    blocked = tmp_path / "blocked"
    shadow = tmp_path / "shadow"
    _write_comparison(blocked, status="blocked", ex_delta=0.0, valid_delta=-0.25, p95_delta=52292.0)
    _write_comparison(
        shadow,
        status="insufficient_semantic_evidence",
        ex_delta=0.0,
        valid_delta=0.0,
        p95_delta=7577.0,
    )

    paths = build_multi_candidate_series_report(
        [blocked, shadow],
        output_dir=tmp_path / "series",
    )

    summary = read_json(paths["summary"])
    rows = read_jsonl(paths["cases"])
    report = paths["report"].read_text(encoding="utf-8")

    assert summary["status_counts"] == {"blocked": 1, "insufficient_semantic_evidence": 1}
    assert summary["best_available_recommendation"] == "do_not_adopt_candidate_adoption"
    assert rows[0]["recommendation"] == "do_not_adopt"
    assert rows[1]["recommendation"] == "shadow_or_disable_until_quality_gain"
    assert "not yet cost-effective" in report
    assert "reliable latency/value tradeoff" in report
    assert "does not run a model" in report
