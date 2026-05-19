from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.evaluation.judge_agreement import analyze_judge_agreement


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare two existing Phase 16 judgment artifacts without calling a model."
    )
    parser.add_argument("left_dir", type=Path)
    parser.add_argument("right_dir", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    paths = analyze_judge_agreement(
        args.left_dir,
        args.right_dir,
        output_dir=args.output_dir,
    )
    print(f"project_root={PROJECT_ROOT}")
    for key, path in paths.items():
        print(f"{key}={path}")


if __name__ == "__main__":
    main()
