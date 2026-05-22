from __future__ import annotations

import argparse

from _bootstrap_path import PROJECT_ROOT  # type: ignore

from src.evaluation.judge_ablation_plan import (
    DEFAULT_JUDGE_MODELS,
    build_dual_policy_judge_ablation_plan,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Plan OpenRouter dual-policy judge commands for a baseline/adaptive benchmark pair "
            "without calling a model."
        )
    )
    parser.add_argument("baseline_artifact_dir")
    parser.add_argument("adaptive_artifact_dir")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument(
        "--judge-models",
        nargs="+",
        default=list(DEFAULT_JUDGE_MODELS),
        help="At least two OpenRouter model IDs for agreement/consensus.",
    )
    parser.add_argument(
        "--python-executable",
        default=r".\.venv\Scripts\python.exe",
        help="Python executable written into the PowerShell runbook.",
    )
    parser.add_argument(
        "--judge-reasoning",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Write judge commands with provider reasoning enabled.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    paths = build_dual_policy_judge_ablation_plan(
        args.baseline_artifact_dir,
        args.adaptive_artifact_dir,
        output_dir=args.output_dir,
        judge_models=args.judge_models,
        python_executable=args.python_executable,
        judge_reasoning=args.judge_reasoning,
    )
    print(f"project_root={PROJECT_ROOT}")
    print(f"manifest={paths['manifest']}")
    print(f"powershell={paths['powershell']}")


if __name__ == "__main__":
    main()
