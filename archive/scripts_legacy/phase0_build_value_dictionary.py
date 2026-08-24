from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from _bootstrap_path import PROJECT_ROOT

DB_PATH = PROJECT_ROOT / "data" / "db" / "vtd_health_research_v1.db"
OUT_PATH = PROJECT_ROOT / "data" / "schema" / "value_dictionary.generated.json"

TEXT_HINTS = (
    "gender", "sex", "diagnosis", "risk", "status", "category", "quality", "treatment",
    "history", "environment", "country", "city", "province", "year_of_study", "diet", "sleep",
)
BINARY_HINTS = ("flag", "has_", "is_", "yes", "no", "suicidal", "depression", "anxiety", "panic")
MAX_DISTINCT = 100
MAX_VALUES_PER_COLUMN = 50


def quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def should_profile_column(column: dict) -> bool:
    name = column["name"].lower()
    typ = (column.get("type") or "").lower()
    if "text" in typ or "char" in typ or "varchar" in typ:
        return True
    return any(h in name for h in TEXT_HINTS + BINARY_HINTS)


def main() -> int:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"DB not found: {DB_PATH}")
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True, timeout=10)
    conn.row_factory = sqlite3.Row
    dictionary = {
        "project": "ADHD-VTD / VTD-Edge / PARS-SQL",
        "artifact": "value_dictionary.generated",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "database_file": str(DB_PATH.relative_to(PROJECT_ROOT)),
        "policy": {
            "max_distinct_profiled": MAX_DISTINCT,
            "max_values_per_column": MAX_VALUES_PER_COLUMN,
            "purpose": "Support value linking such as زن -> Female and افسرده -> depression_flag = 1.",
        },
        "tables": {},
    }
    try:
        tables = [r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name").fetchall()]
        for table in tables:
            table_entry = {"columns": {}}
            columns = [dict(r) for r in conn.execute(f"PRAGMA table_info({quote_ident(table)})").fetchall()]
            for col in columns:
                col_name = col["name"]
                if not should_profile_column(col):
                    continue
                try:
                    distinct_count = conn.execute(
                        f"SELECT COUNT(DISTINCT {quote_ident(col_name)}) AS n FROM {quote_ident(table)} WHERE {quote_ident(col_name)} IS NOT NULL"
                    ).fetchone()["n"]
                except sqlite3.Error as exc:
                    table_entry["columns"][col_name] = {"error": str(exc)}
                    continue
                if distinct_count is None or distinct_count > MAX_DISTINCT:
                    continue
                rows = conn.execute(
                    f"SELECT {quote_ident(col_name)} AS value, COUNT(*) AS count "
                    f"FROM {quote_ident(table)} WHERE {quote_ident(col_name)} IS NOT NULL "
                    f"GROUP BY {quote_ident(col_name)} ORDER BY count DESC, value ASC LIMIT ?",
                    (MAX_VALUES_PER_COLUMN,),
                ).fetchall()
                values = [{"value": r["value"], "count": r["count"]} for r in rows]
                table_entry["columns"][col_name] = {
                    "type": col.get("type"),
                    "distinct_count": distinct_count,
                    "values": values,
                    "manual_aliases_needed": True,
                }
            if table_entry["columns"]:
                dictionary["tables"][table] = table_entry
    finally:
        conn.close()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(dictionary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ Wrote {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
