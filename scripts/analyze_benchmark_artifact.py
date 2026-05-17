from __future__ import annotations

import argparse

from _bootstrap_path import PROJECT_ROOT  # type: ignore

from src.evaluation.artifact_analysis import analyze_benchmark_artifact


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a Phase 11 error-analysis report from a real benchmark artifact."
    )
    parser.add_argument("artifact_dir", help="Path to results/benchmark/<run> directory.")
    parser.add_argument("--output-dir", help="Optional output directory under results/error_analysis.")
    parser.add_argument("--max-examples", type=int, default=20, help="Maximum representative failures to include.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    paths = analyze_benchmark_artifact(
        args.artifact_dir,
        output_dir=args.output_dir,
        max_examples=args.max_examples,
    )
    print(f"project_root={PROJECT_ROOT}")
    print(f"report={paths['report']}")
    print(f"failure_cases={paths['failure_cases']}")
    print(f"summary={paths['summary']}")


if __name__ == "__main__":
    main()
