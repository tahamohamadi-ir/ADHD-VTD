from __future__ import annotations

import argparse

from _bootstrap_path import PROJECT_ROOT  # type: ignore

from src.evaluation.reliability_gate_analysis import analyze_reliability_gate_artifact


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Analyze reliability-gate annotations from an existing benchmark artifact."
    )
    parser.add_argument("artifact_dir", help="Benchmark artifact directory with predictions.jsonl.")
    parser.add_argument("--output-dir", required=True, help="Output directory for gate analysis.")
    parser.add_argument(
        "--recompute-gate",
        action="store_true",
        help="Recompute reliability gate decisions with current code for analysis only.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    paths = analyze_reliability_gate_artifact(
        args.artifact_dir,
        output_dir=args.output_dir,
        recompute_gate=args.recompute_gate,
    )
    print(f"project_root={PROJECT_ROOT}")
    print(f"summary={paths['summary']}")
    print(f"cases={paths['cases']}")
    print(f"report={paths['report']}")


if __name__ == "__main__":
    main()
