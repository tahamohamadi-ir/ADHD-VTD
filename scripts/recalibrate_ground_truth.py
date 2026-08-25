"""Recalibrate gold SQL ground truth against the current database.

Re-executes every case's gold SQL via the read-only executor and writes a NEW
versioned dataset file (never overwrites the input), plus a sidecar report of
failures. Follows AGENTS.md rule 11: version bump + hash + manifest trail.

Usage:
    .\\.venv\\Scripts\\python.exe scripts\\recalibrate_ground_truth.py \
        --input data/questions/dev/dev.json --label recalibrated
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


from src.db.read_only_executor import QueryExecutionResult, ReadOnlyExecutor  # noqa: E402


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _next_version_path(input_path: Path) -> Path:
    base_stem = re.sub(r"_v\d+$", "", input_path.stem)
    versions = sorted(
        p
        for p in input_path.parent.glob(f"{base_stem}_v*.json")
        if not p.name.endswith(".manifest.json") and ".recalibration." not in p.name
    )

    def _version_num(p: Path) -> int:
        digits = "".join(ch for ch in p.stem.rsplit("_v", 1)[-1] if ch.isdigit())
        return int(digits) if digits else 0

    next_n = max((_version_num(p) for p in versions), default=1) + 1
    return input_path.parent / f"{base_stem}_v{next_n}.json"


def recalibrate(input_path: Path, db_path: str | None = None) -> tuple[Path, dict]:
    dataset = json.loads(input_path.read_text(encoding="utf-8-sig"))
    executor = ReadOnlyExecutor()
    failures: list[dict] = []
    executed = 0
    for case in dataset:
        sql = case.get("sql") or case.get("safe_sql")
        case_id = case.get("id", "?")
        if not sql:
            failures.append({"id": case_id, "stage": "missing_sql"})
            continue
        try:
            result: QueryExecutionResult = executor.execute_readonly(sql)
            executed += 1
            if result.error:
                failures.append({"id": case_id, "stage": "execution", "error": str(result.error)})
        except Exception as exc:  # noqa: BLE001 - CLI boundary
            executed += 1
            failures.append({"id": case_id, "stage": "exception", "error": str(exc)[:300]})

    out_path = _next_version_path(input_path)
    out_path.write_text(
        json.dumps(dataset, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input": str(input_path).replace("\\", "/"),
        "input_sha256": _sha256_file(input_path),
        "output": str(out_path).replace("\\", "/"),
        "output_sha256": _sha256_file(out_path),
        "total_cases": len(dataset),
        "executed_ok": executed - len([f for f in failures if f["stage"] != "missing_sql"]),
        "failure_count": len(failures),
        "failures": failures,
    }
    report_path = out_path.with_suffix(".recalibration.json")
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return out_path, report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Dataset JSON path to recalibrate")
    parser.add_argument("--db", default=None, help="Optional DB path override")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"ERROR: input not found: {input_path}")
        return 2
    out_path, report = recalibrate(input_path, args.db)
    print(f"OK  wrote {out_path}")
    print(
        f"    cases={report['total_cases']} "
        f"executed_ok={report['executed_ok']} failures={report['failure_count']}"
    )
    print(f"    report={out_path.with_suffix('.recalibration.json')}")
    return 0 if report["failure_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
