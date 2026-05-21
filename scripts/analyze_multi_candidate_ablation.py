from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.evaluation.multi_candidate_ablation import compare_multi_candidate_ablation


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Compare baseline and adaptive multi-candidate benchmark artifacts without "
            "running a model or inventing semantic labels."
        )
    )
    parser.add_argument("baseline_artifact_dir", type=Path)
    parser.add_argument("adaptive_artifact_dir", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--baseline-dual-policy-dir", type=Path)
    parser.add_argument("--adaptive-dual-policy-dir", type=Path)
    args = parser.parse_args()

    paths = compare_multi_candidate_ablation(
        args.baseline_artifact_dir,
        args.adaptive_artifact_dir,
        output_dir=args.output_dir,
        baseline_dual_policy_dir=args.baseline_dual_policy_dir,
        adaptive_dual_policy_dir=args.adaptive_dual_policy_dir,
    )
    print(f"project_root={PROJECT_ROOT}")
    for key, path in paths.items():
        print(f"{key}={path}")


if __name__ == "__main__":
    main()
