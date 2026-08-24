from __future__ import annotations

import argparse

from _bootstrap_path import PROJECT_ROOT  # type: ignore

from src.evaluation.ablation_report import write_ablation_comparison


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a Phase 11 ablation comparison report from a real ablation manifest."
    )
    parser.add_argument(
        "manifest_path", help="Path to results/ablation/<run>/ablation_manifest.json."
    )
    parser.add_argument(
        "--output-dir", help="Optional output directory. Defaults to the manifest directory."
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    paths = write_ablation_comparison(args.manifest_path, output_dir=args.output_dir)
    print(f"project_root={PROJECT_ROOT}")
    print(f"report={paths['report']}")
    print(f"summary={paths['summary']}")


if __name__ == "__main__":
    main()
