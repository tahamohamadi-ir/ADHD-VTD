from __future__ import annotations

import argparse
import sys
from pathlib import Path

from _bootstrap_path import PROJECT_ROOT  # noqa: F401

from src.evaluation.ablation_runner import build_ablation_job, run_ablation_jobs


def _discover_configs(config_dir: Path) -> list[Path]:
    return sorted(config_dir.glob("A*.yaml"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create or execute Phase 11 ablation manifests. Default mode is dry-run only.",
    )
    parser.add_argument(
        "configs",
        nargs="*",
        type=Path,
        help="Ablation YAML config files. If omitted, --config-dir is scanned for A*.yaml.",
    )
    parser.add_argument(
        "--config-dir",
        type=Path,
        default=Path("experiments/configs"),
        help="Directory to scan for A*.yaml configs when no explicit config is provided.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory where ablation_manifest.json is written.",
    )
    parser.add_argument(
        "--python-executable",
        default=sys.executable,
        help="Python executable used in planned benchmark commands.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually run benchmark commands. Without this flag, only a not_run manifest is written.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="When executing, capture benchmark output instead of streaming it live.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config_paths = list(args.configs) if args.configs else _discover_configs(args.config_dir)
    if not config_paths:
        raise SystemExit(f"No ablation configs found. Checked: {args.config_dir}")

    jobs = [
        build_ablation_job(path, python_executable=args.python_executable) for path in config_paths
    ]
    manifest_path = run_ablation_jobs(
        jobs,
        output_dir=args.output_dir,
        execute=args.execute,
        stream_output=not args.quiet,
    )
    mode = "execute" if args.execute else "dry-run"
    print(f"mode={mode}")
    print(f"jobs={len(jobs)}")
    print(f"manifest={manifest_path}")
    if not args.execute:
        print("result_status=not_run")
        print("note=config manifests are not benchmark results")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
