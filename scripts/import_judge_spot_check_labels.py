from __future__ import annotations

import argparse

from _bootstrap_path import PROJECT_ROOT  # noqa: F401

from src.evaluation.judge_spot_check import import_spot_check_labels


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Import completed spot-check reviewer labels and compute agreement and "
            "Cohen's kappa against the judge labels."
        ),
    )
    parser.add_argument("review_csv", help="Completed judge_spot_check_package.csv with labels.")
    parser.add_argument(
        "--package-summary",
        required=True,
        help="package_summary.json of the spot-check package this CSV was filled from.",
    )
    parser.add_argument(
        "--output-dir", required=True, help="Output directory for the import artifacts."
    )
    parser.add_argument(
        "--authoritative",
        action="store_true",
        help="Mark the import authoritative when every row has a valid non-blank label.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    paths = import_spot_check_labels(
        args.review_csv,
        args.package_summary,
        output_dir=args.output_dir,
        authoritative=args.authoritative,
    )
    print(f"project_root={PROJECT_ROOT}")
    print(f"summary={paths['summary']}")
    print(f"report={paths['report']}")


if __name__ == "__main__":
    main()
