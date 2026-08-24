from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

Measurement = tuple[str, Mapping[str, float]]
LooseMeasurement = tuple[str, Mapping[str, float] | None]


def find_summary_file(directory: str | Path) -> Path | None:
    dir_path = Path(directory)
    if not dir_path.is_dir():
        return None
    for path in sorted(dir_path.glob("*.json")):
        if not path.is_file():
            continue
        try:
            obj = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        if _looks_like_benchmark_summary(obj):
            return path
    return None


def _looks_like_benchmark_summary(obj: Any) -> bool:
    if not isinstance(obj, dict) or not isinstance(obj.get("latency"), dict):
        return False
    try:
        text = json.dumps(obj, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        return False
    return "execution_accuracy" in text or "valid_sql_rate" in text


def extract_latency(summary_json_obj: Any) -> dict[str, float] | None:
    latency = summary_json_obj.get("latency") if isinstance(summary_json_obj, dict) else None
    if not isinstance(latency, dict):
        return None
    extracted: dict[str, float] = {}
    for key, value in latency.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        extracted[str(key)] = float(value)
    if "mean_ms" not in extracted or "p95_ms" not in extracted:
        return None
    return extracted


def missing_latency_names(measurements: Sequence[LooseMeasurement]) -> list[str]:
    return [name for name, latency in measurements if latency is None]


def evaluate_latency_budgets(
    measurements: Sequence[Measurement],
    *,
    baseline: Measurement | None = None,
    max_p95_ms: float | None = None,
    max_mean_ms: float | None = None,
    max_p95_delta_ms: float | None = None,
    max_mean_delta_ms: float | None = None,
) -> list[str]:
    violations: list[str] = []
    delta_configured = max_p95_delta_ms is not None or max_mean_delta_ms is not None
    if delta_configured and baseline is None:
        violations.append("delta budget configured but no baseline measurement provided")
        return violations
    for name, latency in measurements:
        p95 = float(latency["p95_ms"])
        mean = float(latency["mean_ms"])
        if max_p95_ms is not None and p95 > max_p95_ms:
            violations.append(f"{name}: p95_ms={p95:.1f} exceeds absolute budget {max_p95_ms:.1f}")
        if max_mean_ms is not None and mean > max_mean_ms:
            violations.append(
                f"{name}: mean_ms={mean:.1f} exceeds absolute budget {max_mean_ms:.1f}"
            )
        if baseline is not None:
            base_p95 = float(baseline[1]["p95_ms"])
            base_mean = float(baseline[1]["mean_ms"])
            if max_p95_delta_ms is not None and p95 - base_p95 > max_p95_delta_ms:
                violations.append(
                    f"{name}: p95 delta {p95 - base_p95:.1f}ms exceeds budget {max_p95_delta_ms:.1f}"
                )
            if max_mean_delta_ms is not None and mean - base_mean > max_mean_delta_ms:
                violations.append(
                    f"{name}: mean delta {mean - base_mean:.1f}ms exceeds budget "
                    f"{max_mean_delta_ms:.1f}"
                )
    return violations


def collect_measurements(
    directories: Sequence[str],
) -> tuple[list[tuple[str, Path]], list[Measurement], list[str]]:
    resolved: list[tuple[str, Path]] = []
    latencies: list[Measurement] = []
    errors: list[str] = []
    for directory in directories:
        summary_path = find_summary_file(directory)
        if summary_path is None:
            errors.append(f"{directory}: no benchmark summary JSON found")
            continue
        try:
            obj = json.loads(summary_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            errors.append(f"{summary_path}: unreadable summary JSON ({exc})")
            continue
        latency = extract_latency(obj)
        if latency is None:
            errors.append(f"{summary_path}: summary has no usable latency block")
            continue
        resolved.append((directory, summary_path))
        latencies.append((directory, latency))
    return resolved, latencies, errors


def format_markdown_table(
    measurements: Sequence[Measurement],
    summary_by_dir: Mapping[str, Path],
    violations_by_artifact: Mapping[str, list[str]],
) -> str:
    lines = [
        "| artifact | mean_ms | p95_ms | violations |",
        "|---|---|---|---|",
    ]
    for name, latency in measurements:
        artifact_violations = violations_by_artifact.get(name, [])
        cell = "<br>".join(artifact_violations) if artifact_violations else "-"
        lines.append(
            f"| {name} ({summary_by_dir[name].name}) | {latency['mean_ms']:.1f} | "
            f"{latency['p95_ms']:.1f} | {cell} |"
        )
    return "\n".join(lines)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check benchmark artifact latency against absolute and delta budgets."
    )
    parser.add_argument("artifact_dirs", nargs="+", help="benchmark artifact directories")
    parser.add_argument("--baseline-dir", default=None, help="baseline artifact directory")
    parser.add_argument("--max-p95-ms", type=float, default=None)
    parser.add_argument("--max-mean-ms", type=float, default=None)
    parser.add_argument("--max-p95-delta-ms", type=float, default=None)
    parser.add_argument("--max-mean-delta-ms", type=float, default=None)
    parser.add_argument("--json", action="store_true", help="emit a JSON report")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    delta_configured = args.max_p95_delta_ms is not None or args.max_mean_delta_ms is not None
    if delta_configured and args.baseline_dir is None:
        print("[error] --max-p95-delta-ms/--max-mean-delta-ms require --baseline-dir")
        return 3

    resolved, latencies, errors = collect_measurements(args.artifact_dirs)
    baseline: Measurement | None = None
    if args.baseline_dir is not None:
        baseline_resolved, baseline_latencies, baseline_errors = collect_measurements(
            [args.baseline_dir]
        )
        errors.extend(baseline_errors)
        if baseline_resolved:
            baseline = (args.baseline_dir, baseline_latencies[0][1])
    if errors or len(resolved) != len(args.artifact_dirs):
        for error in errors:
            print(f"[error] {error}")
        return 3

    violations = evaluate_latency_budgets(
        latencies,
        baseline=baseline,
        max_p95_ms=args.max_p95_ms,
        max_mean_ms=args.max_mean_ms,
        max_p95_delta_ms=args.max_p95_delta_ms,
        max_mean_delta_ms=args.max_mean_delta_ms,
    )
    summary_by_dir = dict(resolved)
    violations_by_artifact: dict[str, list[str]] = {}
    for violation in violations:
        artifact = violation.split(":", 1)[0]
        violations_by_artifact.setdefault(artifact, []).append(violation)

    if args.json:
        report = {
            "artifacts": [
                {"artifact": name, "summary": str(summary_by_dir[name]), **dict(latency)}
                for name, latency in latencies
            ],
            "baseline": baseline[0] if baseline else None,
            "budgets": {
                "max_p95_ms": args.max_p95_ms,
                "max_mean_ms": args.max_mean_ms,
                "max_p95_delta_ms": args.max_p95_delta_ms,
                "max_mean_delta_ms": args.max_mean_delta_ms,
            },
            "violations": violations,
            "status": "violation" if violations else "ok",
        }
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(format_markdown_table(latencies, summary_by_dir, violations_by_artifact))
        for violation in violations:
            print(f"[violation] {violation}")

    if violations:
        return 2
    if not args.json:
        print("[ok] all latency budgets satisfied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
