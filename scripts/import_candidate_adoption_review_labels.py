from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.evaluation.candidate_adoption_review import (
    import_candidate_adoption_review_labels,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Import completed candidate-adoption review CSV labels into a "
            "dual-policy artifact, or report pending/invalid labels without "
            "inventing correctness."
        )
    )
    parser.add_argument("review_csv", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--reviewer-label", default="human_review_pending")
    parser.add_argument(
        "--authoritative",
        action="store_true",
        help="Mark completed reviewer labels authoritative. Blank or invalid labels keep this false.",
    )
    args = parser.parse_args()

    paths = import_candidate_adoption_review_labels(
        review_csv=args.review_csv,
        output_dir=args.output_dir,
        reviewer_label=args.reviewer_label,
        authoritative=args.authoritative,
    )
    print(f"project_root={PROJECT_ROOT}")
    for key, path in paths.items():
        print(f"{key}={path}")


if __name__ == "__main__":
    main()
