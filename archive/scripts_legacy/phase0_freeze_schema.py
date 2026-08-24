from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from _bootstrap_path import PROJECT_ROOT

DB_PATH = PROJECT_ROOT / "data" / "db" / "vtd_health_research_v1.db"
SCHEMA_DIR = PROJECT_ROOT / "data" / "schema"
AUDIT_DIR = PROJECT_ROOT / "data" / "audit"
OUT_PATH = SCHEMA_DIR / "schema_snapshot.generated.json"
REPORT_PATH = AUDIT_DIR / "schema_freeze_report.md"


def quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def inspect_schema(db_path: Path) -> dict:
    if not db_path.exists():
        raise FileNotFoundError(f"DB not found: {db_path}")

    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        tables = []
        table_rows = conn.execute(
            "SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
        for t in table_rows:
            table_name = t["name"]
            columns = []
            for c in conn.execute(f"PRAGMA table_info({quote_ident(table_name)})").fetchall():
                columns.append({
                    "cid": c["cid"],
                    "name": c["name"],
                    "type": c["type"],
                    "notnull": bool(c["notnull"]),
                    "default_value": c["dflt_value"],
                    "primary_key": bool(c["pk"]),
                })
            fks = []
            for fk in conn.execute(f"PRAGMA foreign_key_list({quote_ident(table_name)})").fetchall():
                fks.append({
                    "id": fk["id"],
                    "seq": fk["seq"],
                    "from": fk["from"],
                    "to_table": fk["table"],
                    "to_column": fk["to"],
                    "on_update": fk["on_update"],
                    "on_delete": fk["on_delete"],
                    "match": fk["match"],
                })
            indexes = []
            for idx in conn.execute(f"PRAGMA index_list({quote_ident(table_name)})").fetchall():
                idx_name = idx["name"]
                idx_cols = [r["name"] for r in conn.execute(f"PRAGMA index_info({quote_ident(idx_name)})").fetchall()]
                indexes.append({"name": idx_name, "unique": bool(idx["unique"]), "columns": idx_cols})
            try:
                row_count = conn.execute(f"SELECT COUNT(*) AS n FROM {quote_ident(table_name)}").fetchone()["n"]
            except sqlite3.Error:
                row_count = None
            tables.append({
                "name": table_name,
                "sql": t["sql"],
                "row_count": row_count,
                "columns": columns,
                "foreign_keys": fks,
                "indexes": indexes,
            })
        return {
            "project": "ADHD-VTD / VTD-Edge / PARS-SQL",
            "artifact": "schema_snapshot.generated",
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "database_file": str(db_path.relative_to(PROJECT_ROOT)),
            "sqlite_version": sqlite3.sqlite_version,
            "table_count": len(tables),
            "tables": tables,
        }
    finally:
        conn.close()


def write_report(snapshot: dict) -> None:
    lines = []
    lines.append("# Schema Freeze Report")
    lines.append("")
    lines.append(f"**Generated at UTC:** {snapshot['generated_at_utc']}  ")
    lines.append(f"**Database:** `{snapshot['database_file']}`  ")
    lines.append(f"**SQLite version:** {snapshot['sqlite_version']}  ")
    lines.append(f"**Table count:** {snapshot['table_count']}  ")
    lines.append("")
    lines.append("## Table Summary")
    lines.append("")
    lines.append("| Table | Rows | Columns | Foreign Keys | Indexes |")
    lines.append("|---|---:|---:|---:|---:|")
    for t in snapshot["tables"]:
        lines.append(f"| `{t['name']}` | {t['row_count']} | {len(t['columns'])} | {len(t['foreign_keys'])} | {len(t['indexes'])} |")
    lines.append("")
    lines.append("## Freeze Decision")
    lines.append("")
    lines.append("- [ ] Review `data/schema/schema_snapshot.generated.json`.")
    lines.append("- [ ] If accepted, copy/update `data/schema/schema_snapshot.json`.")
    lines.append("- [ ] Regenerate value dictionary.")
    lines.append("- [ ] Re-run 50Q audit after any schema change.")
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    SCHEMA_DIR.mkdir(parents=True, exist_ok=True)
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    snapshot = inspect_schema(DB_PATH)
    OUT_PATH.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(snapshot)
    print(f"✅ Wrote {OUT_PATH}")
    print(f"✅ Wrote {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
