from __future__ import annotations

import argparse

from _bootstrap_path import PROJECT_ROOT  # type: ignore

from src.evaluation.dual_policy_report import build_dual_policy_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Merge semantic-user-question and strict-reference judge reports without calling a model."
    )
    parser.add_argument(
        "--semantic-dir",
        required=True,
        help="Agreement or consensus directory for semantic policy.",
    )
    parser.add_argument(
        "--strict-dir", required=True, help="Agreement or consensus directory for strict policy."
    )
    parser.add_argument(
        "--output-dir", required=True, help="Output directory for dual-policy report artifacts."
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    paths = build_dual_policy_report(
        args.semantic_dir,
        args.strict_dir,
        output_dir=args.output_dir,
    )
    print(f"project_root={PROJECT_ROOT}")
    print(f"summary={paths['summary']}")
    print(f"cases={paths['cases']}")
    print(f"report={paths['report']}")


if __name__ == "__main__":
    main()
