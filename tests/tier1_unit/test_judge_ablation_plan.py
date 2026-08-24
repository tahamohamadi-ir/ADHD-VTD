from __future__ import annotations

from src.evaluation.dataset_loader import read_json, write_json
from src.evaluation.judge_ablation_plan import (
    build_dual_policy_judge_ablation_plan,
    validate_dual_policy_judge_ablation_plan,
)


def test_build_dual_policy_judge_ablation_plan_writes_commands_without_results(tmp_path):
    baseline = tmp_path / "baseline_artifact"
    adaptive = tmp_path / "adaptive_artifact"
    baseline.mkdir()
    adaptive.mkdir()

    paths = build_dual_policy_judge_ablation_plan(
        baseline,
        adaptive,
        output_dir=tmp_path / "plan",
        judge_models=["qwen/qwen3.6-plus", "deepseek/deepseek-v4-flash"],
    )

    manifest = read_json(paths["manifest"])
    powershell = paths["powershell"].read_text(encoding="utf-8")
    validation = validate_dual_policy_judge_ablation_plan(paths["manifest"].parent)

    assert manifest["baseline_artifact_dir"] == str(baseline)
    assert manifest["adaptive_artifact_dir"] == str(adaptive)
    assert len(manifest["commands"]) == 19
    assert validation.ok
    assert validation.checked["command_count"] == 19
    assert validation.checked["judge_policy_counts"] == {"semantic": 4, "strict": 4}
    assert "does not call a judge" in manifest["anti_fake_policy"]
    assert "Start-Transcript" in powershell
    assert "Invoke-JudgeStep -Label 'judge_baseline_semantic_qwen_qwen3_6-plus'" in powershell
    assert "'--judge-policy'," in powershell
    assert "'semantic'," in powershell
    assert "'strict'," in powershell
    assert "scripts\\analyze_multi_candidate_ablation.py" in powershell
    assert "--baseline-dual-policy-dir" in powershell
    assert "--adaptive-dual-policy-dir" in powershell


def test_build_dual_policy_judge_ablation_plan_honors_failure_only_mode(tmp_path):
    baseline = tmp_path / "baseline_artifact"
    adaptive = tmp_path / "adaptive_artifact"
    baseline.mkdir()
    adaptive.mkdir()

    paths = build_dual_policy_judge_ablation_plan(
        baseline,
        adaptive,
        output_dir=tmp_path / "plan",
        judge_models=["qwen/qwen3.6-plus", "deepseek/deepseek-v4-flash"],
        all_predictions=False,
    )

    manifest = read_json(paths["manifest"])
    judge_commands = [
        command["command"]
        for command in manifest["commands"]
        if command["label"].startswith("judge_")
    ]

    assert manifest["all_predictions"] is False
    assert all("--all-predictions" not in command for command in judge_commands)
    assert validate_dual_policy_judge_ablation_plan(paths["manifest"].parent).ok


def test_validate_dual_policy_judge_ablation_plan_rejects_command_drift(tmp_path):
    baseline = tmp_path / "baseline_artifact"
    adaptive = tmp_path / "adaptive_artifact"
    baseline.mkdir()
    adaptive.mkdir()
    paths = build_dual_policy_judge_ablation_plan(
        baseline,
        adaptive,
        output_dir=tmp_path / "plan",
        judge_models=["qwen/qwen3.6-plus", "deepseek/deepseek-v4-flash"],
        all_predictions=False,
    )
    manifest = read_json(paths["manifest"])
    manifest["commands"][0]["command"].append("--all-predictions")
    write_json(paths["manifest"], manifest)

    validation = validate_dual_policy_judge_ablation_plan(paths["manifest"].parent)

    assert not validation.ok
    assert {issue.code for issue in validation.issues} == {"PLAN_COMMAND_INVALID"}


def test_build_dual_policy_judge_ablation_plan_requires_two_models(tmp_path):
    baseline = tmp_path / "baseline_artifact"
    adaptive = tmp_path / "adaptive_artifact"
    baseline.mkdir()
    adaptive.mkdir()

    try:
        build_dual_policy_judge_ablation_plan(
            baseline,
            adaptive,
            output_dir=tmp_path / "plan",
            judge_models=["qwen/qwen3.6-plus"],
        )
    except ValueError as exc:
        assert "At least two judge models" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("Expected ValueError")
