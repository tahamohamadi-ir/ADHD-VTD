from __future__ import annotations

from src.evaluation.dataset_loader import write_jsonl
from src.evaluation.export_utils import export_benchmark_csvs, generate_paper_tables


def test_prefixed_benchmark_csv_artifacts_are_written(tmp_path):
    records = [{"id": "VTD-1", "ok": True, "latency_ms": 12}]
    summary = {
        "config": {
            "model_name": "model-a",
            "model_slug": "model_a",
            "ablation_id": "A7",
            "enabled_modules": ["nlu"],
            "disabled_modules": ["reflexion"],
            "dataset": "dev",
            "selection_policy": "samples_per_level",
        },
        "reliability": {"normalized_score": 1.0},
        "error_analysis": {"by_error": {}},
        "latency": {"median_ms": 12},
        "metrics": {"execution_accuracy": {"value": 1.0, "description": "EX"}},
    }

    export_benchmark_csvs(records, summary, tmp_path, prefix="stamp_model_A7")
    generate_paper_tables(summary, tmp_path / "stamp_model_A7_paper_tables.md")
    write_jsonl(tmp_path / "stamp_model_A7_attempts.jsonl", [])

    assert (tmp_path / "stamp_model_A7_benchmark_results.csv").exists()
    assert (tmp_path / "stamp_model_A7_reliability_summary.csv").exists()
    assert (tmp_path / "stamp_model_A7_attempts.jsonl").exists()
    paper_tables = (tmp_path / "stamp_model_A7_paper_tables.md").read_text(encoding="utf-8")
    assert "model_name" in paper_tables
    assert "A7" in paper_tables
