from __future__ import annotations

import argparse

from _bootstrap_path import PROJECT_ROOT  # type: ignore

from src.evaluation.judge_consensus import build_judge_consensus


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build a conservative consensus report from two or more Phase 16 judgment artifacts."
    )
    parser.add_argument(
        "judgment_dirs", nargs="+", help="Paths to results/judgments/<run> directories."
    )
    parser.add_argument(
        "--output-dir", required=True, help="Output directory for consensus artifacts."
    )
    parser.add_argument(
        "--min-agree",
        type=int,
        default=2,
        help="Minimum number of authoritative non-null semantic votes required for a consensus label.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    paths = build_judge_consensus(
        args.judgment_dirs,
        output_dir=args.output_dir,
        min_agree=args.min_agree,
    )
    print(f"project_root={PROJECT_ROOT}")
    print(f"summary={paths['summary']}")
    print(f"cases={paths['cases']}")
    print(f"report={paths['report']}")


if __name__ == "__main__":
    main()
