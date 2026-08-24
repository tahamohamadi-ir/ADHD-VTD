from __future__ import annotations

import json
import hashlib
from collections import Counter
from pathlib import Path
from typing import Any

from scripts.verify_artifact import verify_artifact


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _build_artifact(
    tmp_path: Path,
    *,
    config_updates: dict[str, Any] | None = None,
    include_missing_sql: bool = False,
) -> Path:
    run_dir = tmp_path / "20260626_agent_positive400_final"
    run_dir.mkdir()

    predictions = [
        {
            "id": "case-1",
            "expected_action": "generate_sql",
            "should_generate_sql": True,
            "ok": True,
            "valid_sql": True,
            "execution_correct": True,
            "generated_sql": "SELECT COUNT(*) AS n FROM student_depression",
        },
        {
            "id": "case-2",
            "expected_action": "generate_sql",
            "should_generate_sql": True,
            "ok": False,
            "valid_sql": False,
            "execution_correct": False,
            "generated_sql": "SELECT unknown_column FROM student_depression",
        },
        {
            "id": "case-3",
            "expected_action": "ask_clarification",
            "should_generate_sql": False,
            "actual_action": "ask_clarification",
            "ok": True,
            "generated_sql": None,
        },
    ]
    if include_missing_sql:
        predictions.append(
            {
                "id": "case-4",
                "expected_action": "generate_sql",
                "should_generate_sql": True,
                "ok": False,
                "valid_sql": False,
                "execution_correct": False,
                "generated_sql": None,
                "error": "MISSING_GENERATED_SQL",
            }
        )
    failures = [predictions[1]]
    if include_missing_sql:
        failures.append(predictions[-1])
    config = {
        "config_id": "agent_positive400_final",
        "mode": "agent",
        "dataset_hash": "dataset-hash",
        "selected_cases_hash": "selected-cases-hash",
        "module_flags": {"deterministic_templates": False},
        "judge": {"enabled": False, "provider": "mock"},
        "retrieval_reranker": None,
        "retrieval_reranker_backend": None,
    }
    if config_updates:
        config.update(config_updates)

    prefix = "run"
    paths = {
        "config": run_dir / f"{prefix}_config.json",
        "summary_json": run_dir / f"{prefix}_summary.json",
        "summary_md": run_dir / f"{prefix}_summary.md",
        "predictions": run_dir / f"{prefix}_predictions.jsonl",
        "failures": run_dir / f"{prefix}_failures.jsonl",
        "benchmark_results_csv": run_dir / f"{prefix}_benchmark_results.csv",
    }
    summary = {
        "config": config,
        "dataset": {"total_evaluated": len(predictions)},
        "failures": len(failures),
        "metrics": {
            "execution_accuracy": {"numerator": 1, "denominator": 2, "value": 0.5},
            "conservative_execution_accuracy": {
                "numerator": 1,
                "denominator": 3 if include_missing_sql else 2,
                "value": 1 / 3 if include_missing_sql else 0.5,
            },
            "valid_sql_rate": {"numerator": 1, "denominator": 2, "value": 0.5},
            "missing_sql_count": {
                "numerator": 1 if include_missing_sql else 0,
                "denominator": 3 if include_missing_sql else 2,
                "value": 1 if include_missing_sql else 0,
            },
            "invalid_sql_count": {"numerator": 1, "denominator": 2, "value": 1},
            "result_mismatch_count": {"numerator": 0, "denominator": 2, "value": 0},
            "unsafe_sql_count": {"numerator": 0, "denominator": len(predictions), "value": 0},
        },
        "reliability": {"unsafe_sql": 0},
        "artifacts": {key: str(path) for key, path in paths.items()},
    }

    _write_json(paths["config"], config)
    _write_json(paths["summary_json"], summary)
    paths["summary_md"].write_text("# Summary\n", encoding="utf-8")
    paths["benchmark_results_csv"].write_text("id,ok\ncase-1,true\n", encoding="utf-8")
    _write_jsonl(paths["predictions"], predictions)
    _write_jsonl(paths["failures"], failures)
    _write_json(
        run_dir / "artifact_manifest.json",
        {"completed": {"agent_positive400_final": {"artifact_dir": str(run_dir)}}},
    )
    return run_dir


def _write_dual_policy_artifact(
    root: Path,
    *,
    authoritative: bool = True,
    rows: list[dict[str, Any]] | None = None,
) -> Path:
    root.mkdir()
    dual_rows = rows or [
        {
            "case_id": "case-1",
            "semantic_policy_label": "correct",
            "strict_policy_label": "correct",
            "combined_label": "both_correct",
        }
    ]
    _write_jsonl(root / "dual_policy_cases.jsonl", dual_rows)
    _write_json(
        root / "dual_policy_summary.json",
        {
            "authoritative": authoritative,
            "paper_metric_allowed": False,
            "common_cases": len(dual_rows),
            "semantic_counts": dict(
                Counter(str(row["semantic_policy_label"]) for row in dual_rows)
            ),
            "strict_counts": dict(Counter(str(row["strict_policy_label"]) for row in dual_rows)),
            "combined_counts": dict(Counter(str(row["combined_label"]) for row in dual_rows)),
            "anti_fake_policy": "Synthetic unit-test fixture; no model calls or inferred labels.",
        },
    )
    return root


def _codes(run_dir: Path, **kwargs: Any) -> set[str]:
    return {issue.code for issue in verify_artifact(run_dir, **kwargs).issues}


def test_verify_artifact_accepts_consistent_synthetic_run(tmp_path):
    report = verify_artifact(_build_artifact(tmp_path))

    assert report.ok
    assert report.issues == []
    assert report.checked["prediction_count"] == 3
    assert report.checked["failure_count"] == 1


def test_verify_artifact_accepts_current_dataset_hash(tmp_path):
    dataset_path = tmp_path / "dataset.json"
    dataset_path.write_text('{"cases":[]}\n', encoding="utf-8")
    run_dir = _build_artifact(
        tmp_path,
        config_updates={
            "dataset_path": str(dataset_path),
            "dataset_hash": _sha256_file(dataset_path),
        },
    )

    report = verify_artifact(run_dir)

    assert report.ok
    assert report.checked["dataset_path_exists"] is True
    assert report.checked["current_dataset_hash"] == _sha256_file(dataset_path)


def test_verify_artifact_rejects_dataset_hash_drift(tmp_path):
    dataset_path = tmp_path / "dataset.json"
    dataset_path.write_text('{"cases":[]}\n', encoding="utf-8")
    run_dir = _build_artifact(
        tmp_path,
        config_updates={
            "dataset_path": str(dataset_path),
            "dataset_hash": "old-dataset-hash",
        },
    )

    assert "DATASET_HASH_DRIFT" in _codes(run_dir)


def test_verify_artifact_rejects_missing_dataset_path(tmp_path):
    run_dir = _build_artifact(
        tmp_path,
        config_updates={
            "dataset_path": str(tmp_path / "missing_dataset.json"),
            "dataset_hash": "dataset-hash",
        },
    )

    assert "DATASET_PATH_MISSING" in _codes(run_dir)


def test_verify_artifact_accepts_authoritative_complete_dual_policy_artifact(tmp_path):
    run_dir = _build_artifact(tmp_path)
    dual_policy_dir = _write_dual_policy_artifact(tmp_path / "dual_policy")

    report = verify_artifact(run_dir, dual_policy_dir=dual_policy_dir)

    assert report.ok
    assert report.checked["dual_policy"]["authoritative"] is True
    assert report.checked["dual_policy"]["blocking_counts"] == {}


def test_verify_artifact_rejects_non_authoritative_dual_policy_artifact(tmp_path):
    run_dir = _build_artifact(tmp_path)
    dual_policy_dir = _write_dual_policy_artifact(
        tmp_path / "dual_policy",
        authoritative=False,
    )

    assert "DUAL_POLICY_NOT_AUTHORITATIVE" in _codes(
        run_dir,
        dual_policy_dir=dual_policy_dir,
    )


def test_verify_artifact_rejects_pending_review_import_as_dual_policy_evidence(tmp_path):
    run_dir = _build_artifact(tmp_path)
    pending_dir = tmp_path / "pending_dual_policy"
    pending_dir.mkdir()
    _write_json(
        pending_dir / "candidate_adoption_review_import_summary.json",
        {"status": "pending_review", "pending_rows": ["case-1"]},
    )

    codes = _codes(run_dir, dual_policy_dir=pending_dir)

    assert "DUAL_POLICY_PENDING_REVIEW" in codes
    assert "DUAL_POLICY_SUMMARY_MISSING" in codes


def test_verify_artifact_rejects_incomplete_dual_policy_labels(tmp_path):
    run_dir = _build_artifact(tmp_path)
    dual_policy_dir = _write_dual_policy_artifact(
        tmp_path / "dual_policy",
        rows=[
            {
                "case_id": "case-1",
                "semantic_policy_label": "partial_business_match",
                "strict_policy_label": "correct",
                "combined_label": "partial_or_mixed",
            }
        ],
    )

    assert "DUAL_POLICY_INCOMPLETE_LABELS" in _codes(
        run_dir,
        dual_policy_dir=dual_policy_dir,
    )


def test_verify_artifact_resolves_project_relative_summary_paths(tmp_path, monkeypatch):
    run_dir = _build_artifact(tmp_path)
    summary_path = run_dir / "run_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["artifacts"] = {
        key: str(Path(value).relative_to(tmp_path)) for key, value in summary["artifacts"].items()
    }
    _write_json(summary_path, summary)
    monkeypatch.setattr("scripts.verify_artifact.PROJECT_ROOT", tmp_path)

    report = verify_artifact(run_dir)

    assert report.ok
    assert report.checked["config"] == str(run_dir / "run_config.json")
    assert report.checked["predictions"] == str(run_dir / "run_predictions.jsonl")


def test_verify_artifact_accepts_utf8_bom_manifest(tmp_path):
    run_dir = _build_artifact(tmp_path)
    manifest_path = run_dir / "artifact_manifest.json"
    manifest = {"completed": {"agent_positive400_final": {"artifact_dir": str(run_dir)}}}
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8-sig",
    )

    report = verify_artifact(run_dir)

    assert report.ok


def test_verify_artifact_rejects_prediction_count_mismatch(tmp_path):
    run_dir = _build_artifact(tmp_path)
    summary_path = run_dir / "run_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["dataset"]["total_evaluated"] = 4
    _write_json(summary_path, summary)

    assert "PREDICTION_COUNT_MISMATCH" in _codes(run_dir)


def test_verify_artifact_rejects_missing_sql_count_mismatch(tmp_path):
    run_dir = _build_artifact(tmp_path, include_missing_sql=True)
    summary_path = run_dir / "run_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["metrics"]["missing_sql_count"]["numerator"] = 0
    _write_json(summary_path, summary)

    assert "MISSING_SQL_COUNT_MISMATCH" in _codes(run_dir)


def test_verify_artifact_rejects_missing_deterministic_template_flag(tmp_path):
    run_dir = _build_artifact(tmp_path, config_updates={"module_flags": {}})

    assert "DETERMINISTIC_TEMPLATES_MISSING" in _codes(run_dir)


def test_verify_artifact_rejects_missing_manifest_entry(tmp_path):
    run_dir = _build_artifact(tmp_path)
    _write_json(run_dir / "artifact_manifest.json", {"completed": {"other": {}}})

    assert "MANIFEST_ENTRY_MISSING" in _codes(run_dir)


def test_verify_artifact_rejects_mock_judge_as_authoritative(tmp_path):
    run_dir = _build_artifact(
        tmp_path,
        config_updates={"judge": {"enabled": True, "provider": "mock", "authoritative": True}},
    )

    assert "MOCK_JUDGE_AUTHORITATIVE" in _codes(run_dir)


def test_verify_artifact_rejects_placeholder_reranker_as_real(tmp_path):
    run_dir = _build_artifact(
        tmp_path,
        config_updates={
            "retrieval_reranker": "bge-reranker-v2-m3",
            "retrieval_reranker_backend": "identity",
        },
    )

    assert "PLACEHOLDER_RERANKER_FINAL" in _codes(run_dir)
