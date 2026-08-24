from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from scripts.check_latency_budget import (  # noqa: E402
    collect_measurements,
    evaluate_latency_budgets,
    extract_latency,
    find_summary_file,
    main,
    missing_latency_names,
)

LATENCY = {
    "count": 2,
    "mean_ms": 100.0,
    "median_ms": 100.0,
    "p95_ms": 150.0,
    "min_ms": 50.0,
    "max_ms": 150.0,
}


def _write_json(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def _make_summary_dir(root: Path, name: str, mean_ms: float, p95_ms: float) -> Path:
    artifact = root / name
    _write_json(
        artifact / "run_config.json",
        {"model": "qwen", "mode": "agent"},
    )
    _write_json(
        artifact / "decoy_metrics.json",
        {"metrics": {"execution_accuracy": 0.9, "valid_sql_rate": 1.0}},
    )
    _write_json(
        artifact / "artifact_summary.json",
        {
            "latency": {**LATENCY, "mean_ms": mean_ms, "p95_ms": p95_ms},
            "metrics": {"execution_accuracy": 0.9, "valid_sql_rate": 1.0},
        },
    )
    return artifact


def test_find_summary_file_picks_real_summary_among_decoys(tmp_path):
    artifact = _make_summary_dir(tmp_path, "art1", mean_ms=100.0, p95_ms=150.0)
    found = find_summary_file(artifact)
    assert found is not None
    assert found.name == "artifact_summary.json"


def test_find_summary_file_returns_none_without_summary(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    assert find_summary_file(empty) is None
    assert find_summary_file(tmp_path / "missing") is None


def test_extract_latency_validates_shape():
    assert extract_latency({"latency": LATENCY})["p95_ms"] == 150.0
    assert extract_latency({}) is None
    assert extract_latency({"latency": {"mean_ms": 1.0}}) is None
    assert extract_latency({"latency": {"mean_ms": "fast", "p95_ms": 2}}) is None
    assert extract_latency("not-a-dict") is None


def test_absolute_budget_violation_and_pass():
    measurements = [("art1", {"mean_ms": 300.0, "p95_ms": 800.0})]
    violations = evaluate_latency_budgets(measurements, max_p95_ms=700.0)
    assert len(violations) == 1
    assert "p95" in violations[0]
    assert evaluate_latency_budgets(measurements, max_mean_ms=300.0) == []
    calm = [("art1", {"mean_ms": 100.0, "p95_ms": 200.0})]
    assert evaluate_latency_budgets(calm, max_p95_ms=700.0, max_mean_ms=300.0) == []


def test_mean_absolute_budget_violation():
    violations = evaluate_latency_budgets(
        [("a", {"mean_ms": 400.0, "p95_ms": 10.0})], max_mean_ms=200.0
    )
    assert len(violations) == 1
    assert "mean" in violations[0]


def test_delta_budget_requires_baseline():
    violations = evaluate_latency_budgets(
        [("art", {"mean_ms": 1.0, "p95_ms": 1.0})],
        max_p95_delta_ms=10.0,
    )
    assert violations == ["delta budget configured but no baseline measurement provided"]


def test_delta_budget_violation_and_pass():
    baseline = ("base", {"mean_ms": 100.0, "p95_ms": 200.0})
    candidate = ("cand", {"mean_ms": 120.0, "p95_ms": 260.0})
    violations = evaluate_latency_budgets(
        [candidate], baseline=baseline, max_p95_delta_ms=50.0, max_mean_delta_ms=50.0
    )
    assert len(violations) == 1
    assert "p95 delta" in violations[0]
    ok = evaluate_latency_budgets(
        [candidate], baseline=baseline, max_p95_delta_ms=60.0, max_mean_delta_ms=20.0
    )
    assert ok == []


def test_missing_latency_names_returns_error_markers():
    assert missing_latency_names([("good", {"mean_ms": 1.0, "p95_ms": 2.0}), ("bad", None)]) == [
        "bad"
    ]


def test_collect_measurements_reports_missing_artifact_as_error(tmp_path):
    resolved, latencies, errors = collect_measurements([str(tmp_path / "nope")])
    assert resolved == []
    assert latencies == []
    assert errors and "no benchmark summary JSON found" in errors[0]


def test_main_exit_codes(tmp_path, capsys):
    artifact = _make_summary_dir(tmp_path, "art", mean_ms=29385.6, p95_ms=60832.0)
    assert main([str(artifact), "--max-p95-ms", "70000"]) == 0
    assert main([str(artifact), "--max-p95-ms", "60000"]) == 2
    assert main([str(tmp_path / "missing"), "--max-p95-ms", "70000"]) == 3
    assert main([str(artifact), "--max-p95-delta-ms", "10"]) == 3
    out = capsys.readouterr().out
    assert "| artifact | mean_ms | p95_ms | violations |" in out


def test_main_delta_against_baseline(tmp_path):
    base = _make_summary_dir(tmp_path, "base", mean_ms=29000.0, p95_ms=60000.0)
    cand = _make_summary_dir(tmp_path, "cand", mean_ms=29500.0, p95_ms=65000.0)
    assert (
        main(
            [
                str(cand),
                "--baseline-dir",
                str(base),
                "--max-p95-delta-ms",
                "10000",
                "--max-mean-delta-ms",
                "2000",
            ]
        )
        == 0
    )
    assert (
        main(
            [
                str(cand),
                "--baseline-dir",
                str(base),
                "--max-p95-delta-ms",
                "4000",
            ]
        )
        == 2
    )


def test_main_json_report(tmp_path, capsys):
    artifact = _make_summary_dir(tmp_path, "art", mean_ms=10.0, p95_ms=20.0)
    code = main([str(artifact), "--max-p95-ms", "30", "--json"])
    captured = json.loads(capsys.readouterr().out)
    assert code == 0
    assert captured["status"] == "ok"
    assert captured["artifacts"][0]["p95_ms"] == 20.0
