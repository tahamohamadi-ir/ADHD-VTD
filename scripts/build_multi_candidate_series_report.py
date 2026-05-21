from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.evaluation.multi_candidate_series_report import build_multi_candidate_series_report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Summarize existing multi-candidate A/B reports as cost-benefit evidence."
    )
    parser.add_argument("comparison_dirs", nargs="+", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    paths = build_multi_candidate_series_report(args.comparison_dirs, output_dir=args.output_dir)
    print(f"project_root={PROJECT_ROOT}")
    for key, path in paths.items():
        print(f"{key}={path}")


if __name__ == "__main__":
    main()
