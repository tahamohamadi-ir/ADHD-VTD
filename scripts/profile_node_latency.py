from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from _bootstrap_path import PROJECT_ROOT  # noqa: F401


def iter_records(path: Path):
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)


def _latency_fields(record: dict) -> dict[str, float]:
    fields: dict[str, float] = {}
    for key, value in record.items():
        if (key.endswith("_ms") or "latency" in key.lower()) and isinstance(value, (int, float)):
            fields[str(key)] = float(value)
    return fields


def aggregate_latencies(records) -> dict[str, dict[str, float]]:
    samples: dict[str, list[float]] = {}
    for record in records:
        for field, value in _latency_fields(record).items():
            samples.setdefault(field, []).append(value)

    summary: dict[str, dict[str, float]] = {}
    for field, values in samples.items():
        ordered = sorted(values)
        count = len(ordered)
        mean = sum(ordered) / count
        p95_index = min(count - 1, int(round(0.95 * (count - 1))))
        summary[field] = {
            "count": count,
            "mean_ms": round(mean, 2),
            "p95_ms": round(ordered[p95_index], 2),
            "max_ms": round(ordered[-1], 2),
        }
    return dict(sorted(summary.items(), key=lambda item: item[1]["mean_ms"], reverse=True))


def render_markdown(summary: dict[str, dict[str, float]]) -> str:
    header = "| field | count | mean_ms | p95_ms | max_ms |"
    separator = "|---|---:|---:|---:|---:|"
    rows = [
        f"| {field} | {int(stats['count'])} | {stats['mean_ms']} | {stats['p95_ms']} | "
        f"{stats['max_ms']} |"
        for field, stats in summary.items()
    ]
    return "\n".join([header, separator, *rows]) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Aggregate per-record and component latency fields from benchmark artifacts."
    )
    parser.add_argument("artifact_dirs", nargs="+", help="Benchmark artifact directories.")
    parser.add_argument("--output", help="Optional markdown output path.")
    args = parser.parse_args()

    all_records: list[dict] = []
    for raw_dir in args.artifact_dirs:
        artifact_dir = Path(raw_dir)
        if not artifact_dir.is_dir():
            print(f"Artifact directory not found: {artifact_dir}")
            return 3
        for jsonl_path in sorted(artifact_dir.glob("*predictions*.jsonl")):
            if "partial" in jsonl_path.name:
                continue
            all_records.extend(iter_records(jsonl_path))

    if not all_records:
        print("No prediction records found.")
        return 3

    summary = aggregate_latencies(all_records)
    table = render_markdown(summary)
    print(table)
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(table, encoding="utf-8")
        print(f"wrote {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
