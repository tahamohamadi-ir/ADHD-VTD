"""Check for hallucinated column/table references in gold SQL.

Parses all gold SQL from dataset and verifies every table and column
against schema_snapshot.json.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.schema.schema_registry import SchemaRegistry

DATASET_PATH = Path("data/questions/full/vtd_question_sql_400_merged_validated.json")


def extract_table_refs(sql: str) -> set[str]:
    """Extract table names after FROM / JOIN keywords."""
    pattern = r"\b(?:FROM|JOIN)\s+(\w+)"
    return {m.lower() for m in re.findall(pattern, sql, re.IGNORECASE)}


def extract_column_refs(sql: str, known_tables: set[str]) -> set[str]:
    """Extract column references (table.col or bare col)."""
    # Qualified: table.column
    qualified = re.findall(r"(\w+)\.(\w+)", sql)
    cols = set()
    for t, c in qualified:
        if t.lower() not in (
            "avg",
            "count",
            "sum",
            "min",
            "max",
            "round",
            "coalesce",
            "cast",
            "group",
            "order",
        ):
            cols.add(f"{t.lower()}.{c.lower()}")
    return cols


def main():
    registry = SchemaRegistry()

    data = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    examples = data.get("examples", [])
    print(f"Checking {len(examples)} examples against schema...")

    issues: list[dict] = []
    all_tables = {t.lower() for t in registry.tables}

    for ex in examples:
        eid = ex.get("id", "?")
        sql = ex.get("sql", "")
        if not sql:
            continue

        # Check tables
        tables_in_sql = extract_table_refs(sql)
        for t in tables_in_sql:
            # Skip CTE aliases and subquery aliases
            if t.lower() in (
                "select",
                "where",
                "as",
                "on",
                "and",
                "or",
                "not",
                "null",
                "true",
                "false",
            ):
                continue
            if t not in all_tables:
                # Could be a CTE alias — check if defined in WITH
                if re.search(rf"\bWITH\b.*\b{t}\b\s+AS\s*\(", sql, re.IGNORECASE | re.DOTALL):
                    continue
                issues.append({"id": eid, "type": "unknown_table", "ref": t, "sql": sql[:120]})

        # Check qualified columns
        cols_in_sql = extract_column_refs(sql, all_tables)
        for fq in cols_in_sql:
            tbl, col = fq.split(".", 1)
            if tbl in all_tables and not registry.has_column(tbl, col):
                issues.append({"id": eid, "type": "unknown_column", "ref": fq, "sql": sql[:120]})

    # Write report
    report_dir = Path("results/data_quality")
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "hallucinated_columns_report.md"

    lines = [
        "# Hallucinated Column/Table References Report",
        "",
        f"**Dataset:** `{DATASET_PATH.name}`  ",
        f"**Examples checked:** {len(examples)}  ",
        f"**Issues found:** {len(issues)}  ",
        "",
    ]

    if not issues:
        lines.append("✅ **No hallucinated references found.**")
        print(f"\n✅ No hallucinated references in {len(examples)} examples.")
    else:
        lines.append("| # | Case ID | Type | Reference | SQL (truncated) |")
        lines.append("|---|---|---|---|---|")
        for i, iss in enumerate(issues, 1):
            lines.append(f"| {i} | {iss['id']} | {iss['type']} | `{iss['ref']}` | `{iss['sql']}` |")
        print(f"\n❌ {len(issues)} hallucinated reference(s) found:")
        for iss in issues[:10]:
            print(f"  [{iss['id']}] {iss['type']}: {iss['ref']}")
        if len(issues) > 10:
            print(f"  ... and {len(issues) - 10} more")

    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nReport: {report_path}")
    sys.exit(1 if issues else 0)


if __name__ == "__main__":
    main()
