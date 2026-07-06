from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.evaluation.candidate_adoption_review import (
    build_candidate_adoption_review_package,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Build a non-authoritative human review packet for adopted non-primary "
            "candidate SQL cases from an existing benchmark artifact without "
            "exporting gold SQL or strict correctness labels."
        )
    )
    parser.add_argument("adaptive_artifact_dir", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--reviewer-label", default="human_review_pending")
    args = parser.parse_args()

    paths = build_candidate_adoption_review_package(
        adaptive_artifact_dir=args.adaptive_artifact_dir,
        output_dir=args.output_dir,
        reviewer_label=args.reviewer_label,
    )
    print(f"project_root={PROJECT_ROOT}")
    for key, path in paths.items():
        print(f"{key}={path}")


if __name__ == "__main__":
    main()
