"""Validate all gold SQL from datasets by executing against the actual DB.

For each SQL:
1. Safety validation
2. Schema validation
3. Actual execution in read-only mode
4. Record: OK / FAIL / SYNTAX_ERROR / SCHEMA_ERROR / EMPTY_RESULT
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config.paths import DB_PATH
from src.db.read_only_executor import ReadOnlyExecutor
from src.sql_validation.safety_validator import SQLSafetyValidator
from src.sql_validation.schema_validator import SQLSchemaValidator
from src.utils.jsonl import write_jsonl

DATASET_PATH = Path("data/questions/full/vtd_question_sql_400_merged_validated.json")


def main():
    data = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    examples = data.get("examples", [])
    print(f"Validating {len(examples)} gold SQL queries against {DB_PATH}...")

    safety = SQLSafetyValidator()
    schema = SQLSchemaValidator()
    executor = ReadOnlyExecutor(db_path=str(DB_PATH))

    results: list[dict] = []
    counts = {
        "OK": 0,
        "FAIL": 0,
        "SYNTAX_ERROR": 0,
        "SCHEMA_ERROR": 0,
        "EMPTY_RESULT": 0,
        "SAFETY_FAIL": 0,
        "NO_SQL": 0,
    }
    start = time.perf_counter()

    for ex in examples:
        eid = ex.get("id", "?")
        sql = ex.get("sql", "")
        record = {"id": eid, "sql": sql[:200], "status": "UNKNOWN", "error": None}

        if not sql:
            record["status"] = "NO_SQL"
            counts["NO_SQL"] += 1
            results.append(record)
            continue

        # Safety check
        sr = safety.validate(sql)
        if not sr.ok:
            record["status"] = "SAFETY_FAIL"
            record["error"] = "; ".join(sr.messages())
            counts["SAFETY_FAIL"] += 1
            results.append(record)
            continue

        # Schema check
        scr = schema.validate(sql)
        if not scr.ok:
            record["status"] = "SCHEMA_ERROR"
            record["error"] = "; ".join(scr.messages())
            counts["SCHEMA_ERROR"] += 1
            results.append(record)
            continue

        # Execution
        try:
            er = executor.execute_readonly(sql)
            if not er.ok:
                record["status"] = "FAIL"
                record["error"] = er.error
                counts["FAIL"] += 1
            elif er.row_count == 0:
                record["status"] = "EMPTY_RESULT"
                record["row_count"] = 0
                counts["EMPTY_RESULT"] += 1
            else:
                record["status"] = "OK"
                record["row_count"] = er.row_count
                counts["OK"] += 1
        except Exception as exc:
            record["status"] = "SYNTAX_ERROR"
            record["error"] = str(exc)[:200]
            counts["SYNTAX_ERROR"] += 1

        results.append(record)

    elapsed = (time.perf_counter() - start) * 1000

    # Write JSONL results
    report_dir = Path("results/data_quality")
    report_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(report_dir / "sql_validation_results.jsonl", results)

    # Write markdown report
    total = len(examples)
    pass_rate = counts["OK"] / total * 100 if total else 0
    lines = [
        "# Dataset SQL Validation Report",
        "",
        f"**Dataset:** `{DATASET_PATH.name}`  ",
        f"**Total examples:** {total}  ",
        f"**DB:** `{DB_PATH.name}`  ",
        f"**Elapsed:** {elapsed:.0f}ms  ",
        "",
        "## Summary",
        "",
        "| Status | Count | % |",
        "|---|---|---|",
    ]
    for status, count in sorted(counts.items()):
        pct = count / total * 100 if total else 0
        emoji = "✅" if status == "OK" else ("⚠️" if status == "EMPTY_RESULT" else "❌")
        lines.append(f"| {emoji} {status} | {count} | {pct:.1f}% |")

    lines.append(
        f"\n**Pass Rate (OK + EMPTY_RESULT): {(counts['OK'] + counts['EMPTY_RESULT']) / total * 100:.1f}%**"
    )

    # Failures detail
    failures = [r for r in results if r["status"] not in ("OK", "EMPTY_RESULT")]
    if failures:
        lines.extend(["", "## Failures", "", "| # | ID | Status | Error |", "|---|---|---|---|"])
        for i, f in enumerate(failures[:50], 1):
            lines.append(f"| {i} | {f['id']} | {f['status']} | `{(f.get('error') or '')[:80]}` |")
        if len(failures) > 50:
            lines.append(f"\n*... and {len(failures) - 50} more failures*")

    report_path = report_dir / "dataset_sql_validation_report.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")

    print(f"\n{'=' * 50}")
    print(f"  OK:           {counts['OK']:>4}")
    print(f"  EMPTY_RESULT: {counts['EMPTY_RESULT']:>4}")
    print(f"  SCHEMA_ERROR: {counts['SCHEMA_ERROR']:>4}")
    print(f"  SAFETY_FAIL:  {counts['SAFETY_FAIL']:>4}")
    print(f"  SYNTAX_ERROR: {counts['SYNTAX_ERROR']:>4}")
    print(f"  FAIL:         {counts['FAIL']:>4}")
    print(f"  NO_SQL:       {counts['NO_SQL']:>4}")
    print(f"{'=' * 50}")
    print(f"  Pass Rate: {pass_rate:.1f}%")
    print(f"  Elapsed: {elapsed:.0f}ms")
    print(f"\nReports: {report_dir}")
    sys.exit(0 if pass_rate >= 95 else 1)


if __name__ == "__main__":
    main()
