from __future__ import annotations

import argparse

from _bootstrap_path import PROJECT_ROOT  # type: ignore

from src.evaluation.llm_judge import judge_benchmark_artifact


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create Phase 16 judgment artifacts from an existing benchmark artifact."
    )
    parser.add_argument("artifact_dir", help="Path to results/benchmark/<run> directory.")
    parser.add_argument("--output-dir", help="Optional output directory under results/judgments.")
    parser.add_argument(
        "--judge-provider",
        default="mock",
        choices=["mock", "openrouter"],
        help="Judge provider. openrouter requires OPENROUTER_API_KEY.",
    )
    parser.add_argument(
        "--judge-model",
        help="Provider model id, for example qwen/qwen3.6-plus or deepseek/deepseek-v4-flash.",
    )
    parser.add_argument(
        "--judge-policy",
        default="semantic",
        choices=["semantic", "strict"],
        help=(
            "semantic judges whether SQL answers the user's question; strict judges against the "
            "reference/gold output contract."
        ),
    )
    parser.add_argument(
        "--judge-reasoning",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Enable provider reasoning mode when supported. Use --no-judge-reasoning to force it off.",
    )
    parser.add_argument(
        "--judge-sample-size",
        type=int,
        help="Limit the number of selected predictions to judge.",
    )
    parser.add_argument(
        "--all-predictions",
        action="store_true",
        help="Judge all predictions instead of failures only.",
    )
    parser.add_argument(
        "--case-ids",
        nargs="+",
        help="Optional case IDs to judge. Combine with --all-predictions when selected cases include successful predictions.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    paths = judge_benchmark_artifact(
        args.artifact_dir,
        output_dir=args.output_dir,
        provider_name=args.judge_provider,
        judge_model=args.judge_model,
        reasoning_enabled=args.judge_reasoning,
        failures_only=not args.all_predictions,
        sample_size=args.judge_sample_size,
        case_ids=args.case_ids,
        judge_policy=args.judge_policy,
    )
    print(f"project_root={PROJECT_ROOT}")
    print(f"judgments={paths['judgments']}")
    print(f"summary={paths['summary']}")
    print(f"costs={paths['costs']}")
    print(f"semantic_summary={paths['semantic_summary']}")
    print(f"reasoning={paths['reasoning']}")


if __name__ == "__main__":
    main()
