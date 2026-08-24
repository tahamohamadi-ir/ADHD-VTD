from __future__ import annotations

import json
from pathlib import Path

from src.evaluation.ablation_runner import build_ablation_job, run_ablation_jobs


def _write_config(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "config_id: A0_unit",
                "ablation_id: A0_unit",
                "mode: agent",
                "dataset:",
                "  split: dev",
                "sampling:",
                "  samples_per_level: 2",
                "features:",
                "  nlu: false",
                "  cag: false",
                "  value_linking: true",
                "  reliability_gate: true",
                "  validation: true",
                "  safety: false",
                "reporting:",
                "  result_status: config_only_not_a_result",
            ]
        ),
        encoding="utf-8",
    )


def test_build_ablation_job_records_command_and_declared_flags(tmp_path):
    config_path = tmp_path / "A0_unit.yaml"
    _write_config(config_path)

    job = build_ablation_job(config_path, python_executable="py")

    assert job.config_id == "A0_unit"
    assert job.ablation_id == "A0_unit"
    assert job.command == [
        "py",
        "scripts\\run_benchmark.py",
        "--config",
        str(config_path),
    ]
    assert job.declared_features == {
        "nlu": False,
        "cag": False,
        "value_linking": True,
        "reliability_gate": True,
        "validation": True,
        "safety": False,
    }
    assert job.dataset == {"split": "dev"}
    assert job.sampling == {"samples_per_level": 2}
    assert job.runtime_contract["runtime_enforced"] == {
        "cag": False,
        "nlu": False,
        "reliability_gate": True,
        "value_linking": True,
    }
    assert job.runtime_contract["runtime_locked"] == {"safety": True, "validation": True}
    assert job.runtime_contract["metadata_only"] == {}
    assert job.runtime_contract["warnings"]
    assert job.result_status == "not_run"


def test_run_ablation_jobs_dry_run_writes_not_run_manifest(tmp_path):
    config_path = tmp_path / "A0_unit.yaml"
    output_dir = tmp_path / "manifest"
    _write_config(config_path)
    job = build_ablation_job(config_path)

    manifest_path = run_ablation_jobs([job], output_dir=output_dir, execute=False)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["anti_fake_policy"]
    assert manifest["jobs"][0]["result_status"] == "not_run"
    assert manifest["jobs"][0]["artifact_dir"] is None
    assert manifest["jobs"][0]["declared_features"]["validation"] is True
    assert manifest["jobs"][0]["runtime_contract"]["runtime_locked"]["safety"] is True
    assert "not_run jobs are config manifests only" in manifest["anti_fake_policy"]


def test_retrieval_ablation_parameters_are_not_reported_as_unknown_flags(tmp_path):
    config_path = tmp_path / "R0_unit.yaml"
    config_path.write_text(
        "\n".join(
            [
                "config_id: R0_unit",
                "ablation_id: R0_unit",
                "mode: retrieval",
                "dataset:",
                "  split: dev",
                "sampling:",
                "  samples_per_level: 2",
                "features:",
                "  retrieval_backend: bm25",
                "  reranker: identity",
            ]
        ),
        encoding="utf-8",
    )

    job = build_ablation_job(config_path)

    assert job.runtime_contract["runtime_parameters"] == {
        "reranker": "identity",
        "retrieval_backend": "bm25",
    }
    assert job.runtime_contract["unknown"] == {}


def test_reliability_review_policy_flag_is_runtime_enforced(tmp_path):
    config_path = tmp_path / "A7_review_gate.yaml"
    config_path.write_text(
        "\n".join(
            [
                "config_id: A7_review_gate",
                "ablation_id: A7_review_gate",
                "mode: agent",
                "features:",
                "  reliability_gate: true",
                "  reliability_gate_review_consistency_failures: true",
            ]
        ),
        encoding="utf-8",
    )

    job = build_ablation_job(config_path)

    assert job.runtime_contract["runtime_enforced"]["reliability_gate"] is True
    assert job.runtime_contract["runtime_enforced"]["reliability_gate_review_consistency_failures"] is True
    assert job.runtime_contract["unknown"] == {}
