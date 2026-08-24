from __future__ import annotations

import argparse

from _bootstrap_path import PROJECT_ROOT  # noqa: F401

from src.evaluation.judge_adjudication import adjudicate_consensus


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Apply human CSV decisions or third-judge judgments to a judge consensus "
            "artifact and recompute label counts."
        ),
    )
    parser.add_argument(
        "consensus_dir",
        help="Directory containing judge_consensus.json and judge_consensus_cases.jsonl.",
    )
    parser.add_argument(
        "decisions_csv",
        nargs="?",
        default=None,
        help=(
            "CSV of adjudication decisions with columns case_id and adjudicated_label "
            "(semantic_correct | semantic_incorrect | partial_business_match). "
            "Use this OR --third-judge-dir."
        ),
    )
    parser.add_argument(
        "--third-judge-dir",
        action="append",
        default=[],
        dest="third_judge_dirs",
        help="Judgment directory (judge_summary.json + judgments.jsonl) used as a third judge; repeatable.",
    )
    parser.add_argument(
        "--output-dir", required=True, help="Output directory for adjudicated consensus artifacts."
    )
    parser.add_argument(
        "--fail-on-unresolved",
        action="store_true",
        help="Exit with an error if any case still requires adjudication after applying decisions.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if not args.decisions_csv and not args.third_judge_dirs:
        parser.error("Provide a decisions CSV or at least one --third-judge-dir.")
    try:
        paths = adjudicate_consensus(
            args.consensus_dir,
            output_dir=args.output_dir,
            decisions_csv=args.decisions_csv,
            third_judge_dirs=args.third_judge_dirs,
            fail_on_unresolved=args.fail_on_unresolved,
        )
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc
    print(f"project_root={PROJECT_ROOT}")
    print(f"summary={paths['summary']}")
    print(f"cases={paths['cases']}")
    print(f"report={paths['report']}")


if __name__ == "__main__":
    main()
