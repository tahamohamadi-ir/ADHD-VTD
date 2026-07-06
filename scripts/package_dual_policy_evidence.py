from __future__ import annotations

import argparse

from _bootstrap_path import PROJECT_ROOT  # type: ignore

from src.evaluation.dual_policy_packaging import build_dual_policy_evidence_package
from scripts.verify_artifact import verify_artifact


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Package benchmark and dual-policy artifacts into paper-facing tables without "
            "calling a model or creating new labels."
        )
    )
    parser.add_argument("benchmark_dir", help="Benchmark artifact directory.")
    parser.add_argument(
        "dual_policy_dir", help="Dual-policy report artifact directory."
    )
    parser.add_argument(
        "--output-dir", required=True, help="Output directory for evidence package."
    )
    parser.add_argument(
        "--evidence-label",
        default="small_dev_a4_slice",
        help="Explicit scope label to print in the report.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    verification = verify_artifact(
        args.benchmark_dir,
        dual_policy_dir=args.dual_policy_dir,
    )
    if not verification.ok:
        print(f"project_root={PROJECT_ROOT}")
        print("artifact_verification=failed")
        for issue in verification.issues:
            print(f"{issue.code}: {issue.message}")
        raise SystemExit(1)

    paths = build_dual_policy_evidence_package(
        benchmark_dir=args.benchmark_dir,
        dual_policy_dir=args.dual_policy_dir,
        output_dir=args.output_dir,
        evidence_label=args.evidence_label,
    )
    print(f"project_root={PROJECT_ROOT}")
    print(f"summary={paths['summary']}")
    print(f"cases_csv={paths['cases_csv']}")
    print(f"report={paths['report']}")


if __name__ == "__main__":
    main()
