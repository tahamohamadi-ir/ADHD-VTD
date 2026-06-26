from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from _bootstrap_path import PROJECT_ROOT  # noqa: F401


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return data


def _write_json(path: Path, data: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Merge split run_ablation.py manifests into one analyzable ablation_manifest.json.",
    )
    parser.add_argument("manifest_paths", nargs="+", help="Input ablation_manifest.json files.")
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory where the merged ablation_manifest.json will be written.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    jobs: list[dict[str, Any]] = []
    sources: list[str] = []
    seen: set[str] = set()

    for raw_path in args.manifest_paths:
        path = Path(raw_path)
        manifest = _read_json(path)
        sources.append(str(path))
        for job in manifest.get("jobs", []):
            if not isinstance(job, dict):
                raise ValueError(f"Invalid job entry in {path}")
            key = str(job.get("config_id") or job.get("config_path") or len(jobs))
            if key in seen:
                raise ValueError(f"Duplicate config_id in manifests: {key}")
            seen.add(key)
            jobs.append(job)

    output_path = Path(args.output_dir) / "ablation_manifest.json"
    merged = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "result_policy": "Merged from split run_ablation.py manifests. Cite only jobs with result_status=completed and valid artifact_dir.",
        "anti_fake_policy": "This merge script copies completed job records only; it does not run models or infer missing metrics.",
        "merged_from": sources,
        "jobs": jobs,
    }
    _write_json(output_path, merged)
    completed = sum(1 for job in jobs if job.get("result_status") == "completed")
    print(f"project_root={PROJECT_ROOT}")
    print(f"jobs={len(jobs)}")
    print(f"completed={completed}")
    print(f"manifest={output_path}")


if __name__ == "__main__":
    main()
