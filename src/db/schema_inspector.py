from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

try:
    from src.db.sqlite_connection import get_readonly_connection
except Exception:  # pragma: no cover
    from sqlite_connection import get_readonly_connection


class SchemaInspector:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)

    def inspect(self) -> dict:
        with get_readonly_connection(self.db_path) as conn:
            sqlite_version = conn.execute("select sqlite_version()").fetchone()[0]
            table_rows = conn.execute(
                "SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            ).fetchall()
            tables = []
            for row in table_rows:
                name = row["name"]
                columns = [dict(c) for c in conn.execute(f"PRAGMA table_info({name})").fetchall()]
                fks = [
                    dict(fk) for fk in conn.execute(f"PRAGMA foreign_key_list({name})").fetchall()
                ]
                indexes = []
                for idx in conn.execute(f"PRAGMA index_list({name})").fetchall():
                    idx_d = dict(idx)
                    idx_d["columns"] = [
                        c["name"]
                        for c in conn.execute(f"PRAGMA index_info({idx_d['name']})").fetchall()
                    ]
                    indexes.append(idx_d)
                count = conn.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
                tables.append(
                    {
                        "name": name,
                        "sql": row["sql"],
                        "row_count": count,
                        "columns": columns,
                        "foreign_keys": fks,
                        "indexes": indexes,
                    }
                )
            return {
                "project": "ADHD-VTD / VTD-Edge / PARS-SQL",
                "artifact": "schema_snapshot.generated",
                "generated_at_utc": datetime.now(timezone.utc).isoformat(),
                "database_file": str(self.db_path),
                "sqlite_version": sqlite_version,
                "table_count": len(tables),
                "tables": tables,
            }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    snapshot = SchemaInspector(args.db).inspect()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Schema snapshot written to: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
