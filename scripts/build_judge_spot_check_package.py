from __future__ import annotations

import argparse
from pathlib import Path

from _bootstrap_path import PROJECT_ROOT  # noqa: F401

from src.evaluation.judge_spot_check import build_spot_check_package


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Build a redacted, stratified human spot-check package from an "
            "authoritative judge artifact."
        ),
    )
    parser.add_argument(
        "judgment_dir", help="Input results/judgments/<run> directory with authoritative rows."
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=40,
        help="Number of cases to sample (stratified by judge semantic label).",
    )
    parser.add_argument("--seed", type=int, default=187, help="Deterministic sampling seed.")
    parser.add_argument(
        "--output-dir", required=True, help="Output directory for the spot-check package."
    )
    parser.add_argument(
        "--predictions-file",
        type=Path,
        default=None,
        help=(
            "Optional benchmark predictions JSONL used to enrich the CSV question "
            "column (case_id -> question); never adds SQL or gold fields."
        ),
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    paths = build_spot_check_package(
        args.judgment_dir,
        n=args.sample_size,
        seed=args.seed,
        output_dir=args.output_dir,
        predictions_file=args.predictions_file,
    )
    print(f"project_root={PROJECT_ROOT}")
    print(f"csv={paths['csv']}")
    print(f"summary={paths['summary']}")
    print(f"instructions={paths['instructions']}")


if __name__ == "__main__":
    main()
