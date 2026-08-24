from __future__ import annotations

from src.evaluation.dataset_loader import read_json
from src.evaluation.judge_ablation_plan import build_dual_policy_judge_ablation_plan


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

    assert manifest["baseline_artifact_dir"] == str(baseline)
    assert manifest["adaptive_artifact_dir"] == str(adaptive)
    assert len(manifest["commands"]) == 19
    assert "does not call a judge" in manifest["anti_fake_policy"]
    assert "Start-Transcript" in powershell
    assert "Invoke-JudgeStep -Label 'judge_baseline_semantic_qwen_qwen3_6-plus'" in powershell
    assert "'--judge-policy'," in powershell
    assert "'semantic'," in powershell
    assert "'strict'," in powershell
    assert "scripts\\analyze_multi_candidate_ablation.py" in powershell
    assert "--baseline-dual-policy-dir" in powershell
    assert "--adaptive-dual-policy-dir" in powershell


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
