from __future__ import annotations

from pathlib import Path

from src.evaluation.ablation_report import build_ablation_comparison, write_ablation_comparison
from src.evaluation.dataset_loader import read_json, write_json


def _write_summary(artifact_dir: Path, *, prefix: str, ex: float, valid_sql: float) -> None:
    artifact_dir.mkdir(parents=True)
    write_json(
        artifact_dir / f"{prefix}_summary.json",
        {
            "config": {
                "dataset_hash": "dataset-hash",
                "selected_cases_hash": "selected-cases-hash",
                "module_flags": {"nlu": True},
                "ablation_runtime_contract": {
                    "runtime_enforced": {"nlu": True},
                    "runtime_locked": {"safety": True, "validation": True},
                    "metadata_only": {},
                    "warnings": [],
                },
            },
            "dataset": {"total_evaluated": 8},
            "metrics": {
                "execution_accuracy": {"value": ex},
                "valid_sql_rate": {"value": valid_sql},
            },
            "reliability": {"score": -1.0, "unsafe_sql": 0},
            "latency": {"mean_ms": 12.5, "p95_ms": 25.0},
        },
    )


def _write_retrieval_summary(artifact_dir: Path, *, prefix: str) -> None:
    artifact_dir.mkdir(parents=True)
    write_json(
        artifact_dir / f"{prefix}_summary.json",
        {
            "config": {
                "mode": "retrieval",
                "dataset_hash": "dataset-hash",
                "selected_cases_hash": "selected-cases-hash",
                "retrieval_backend": "bm25",
                "retrieval_reranker": None,
            },
            "dataset": {"total_evaluated": 8},
            "metrics": {
                "retrieval_hit_rate": {"value": 1.0},
                "retrieval_miss_rate": {"value": 0.0},
            },
            "latency": {"mean_ms": 1.5, "p95_ms": 9.0},
        },
    )


def _write_manifest(root: Path, completed_artifact: Path) -> Path:
    manifest = {
        "jobs": [
            {
                "config_id": "A0_unit",
                "ablation_id": "A0_unit",
                "result_status": "completed",
                "artifact_dir": str(completed_artifact),
                "runtime_contract": {"runtime_enforced": {"nlu": False}},
            },
            {
                "config_id": "A1_not_run",
                "ablation_id": "A1_not_run",
                "result_status": "not_run",
                "artifact_dir": None,
            },
        ]
    }
    return write_json(root / "ablation_manifest.json", manifest)


def test_build_ablation_comparison_reads_only_completed_real_summaries(tmp_path):
    artifact = tmp_path / "benchmark" / "A0"
    _write_summary(artifact, prefix="unit", ex=0.25, valid_sql=0.875)
    manifest_path = _write_manifest(tmp_path, artifact)

    report = build_ablation_comparison(manifest_path)

    assert report["jobs_total"] == 2
    assert report["jobs_completed"] == 1
    assert report["same_dataset_hash"] is True
    assert report["same_selected_cases_hash"] is True
    completed = report["rows"][0]
    assert completed["config_id"] == "A0_unit"
    assert completed["execution_accuracy"] == 0.25
    assert completed["valid_sql_rate"] == 0.875
    assert completed["unsafe_sql"] == 0
    assert report["rows"][1]["complete"] is False


def test_write_ablation_comparison_writes_markdown_and_json_with_guardrail(tmp_path):
    artifact = tmp_path / "benchmark" / "A0"
    _write_summary(artifact, prefix="unit", ex=0.25, valid_sql=0.875)
    manifest_path = _write_manifest(tmp_path, artifact)
    output_dir = tmp_path / "report"

    paths = write_ablation_comparison(manifest_path, output_dir=output_dir)

    assert paths["report"].exists()
    assert paths["summary"].exists()
    markdown = paths["report"].read_text(encoding="utf-8")
    summary = read_json(paths["summary"])
    assert "Phase 11 A0-A7 Ablation Comparison" in markdown
    assert "does not run a model" in markdown
    assert "| A0_unit | 8 | 0.25 | 0.875 | -1.0 | 0 | 12.5 | 25.0 |" in markdown
    assert summary["rows"][0]["summary_path"].endswith("_summary.json")


def test_retrieval_ablation_comparison_reports_retrieval_metrics(tmp_path):
    artifact = tmp_path / "benchmark" / "R0"
    _write_retrieval_summary(artifact, prefix="unit")
    manifest = {
        "jobs": [
            {
                "config_id": "R0_unit",
                "ablation_id": "R0_unit",
                "result_status": "completed",
                "artifact_dir": str(artifact),
                "runtime_contract": {
                    "runtime_parameters": {"retrieval_backend": "bm25"},
                    "runtime_enforced": {},
                    "runtime_locked": {},
                    "metadata_only": {},
                    "warnings": [],
                },
            }
        ]
    }
    manifest_path = write_json(tmp_path / "ablation_manifest.json", manifest)

    paths = write_ablation_comparison(manifest_path, output_dir=tmp_path / "report")

    markdown = paths["report"].read_text(encoding="utf-8")
    summary = read_json(paths["summary"])
    assert "Phase 11 Retrieval Ablation Comparison" in markdown
    assert "| R0_unit | bm25 | none | 8 | 1.0 | 0.0 | 1.5 | 9.0 |" in markdown
    assert summary["rows"][0]["retrieval_hit_rate"] == 1.0
