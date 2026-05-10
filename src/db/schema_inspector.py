from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any

from src.config.paths import DEFAULT_DB_PATH, DEFAULT_SCHEMA_SNAPSHOT_PATH, resolve_project_path


class SQLiteSchemaInspector:
    """
    Inspects a SQLite database and exports a schema snapshot usable by schema linking.
    """

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = resolve_project_path(db_path)

    def connect(self) -> sqlite3.Connection:
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found: {self.db_path}")
        return sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)

    def list_tables(self) -> list[str]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                  AND name NOT LIKE 'sqlite_%'
                ORDER BY name
                """
            ).fetchall()
        return [row[0] for row in rows]

    def inspect_table(self, table_name: str) -> dict[str, Any]:
        with self.connect() as conn:
            column_rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
            fk_rows = conn.execute(f"PRAGMA foreign_key_list({table_name})").fetchall()

        columns: dict[str, Any] = {}
        primary_key: list[str] = []

        for cid, name, col_type, notnull, default_value, pk in column_rows:
            columns[name] = {
                "type": col_type or "UNKNOWN",
                "not_null": bool(notnull),
                "default": default_value,
                "primary_key_position": int(pk),
            }
            if pk:
                primary_key.append(name)

        foreign_keys = [
            {
                "column": row[3],
                "ref_table": row[2],
                "ref_column": row[4],
            }
            for row in fk_rows
        ]

        return {
            "description": "",
            "primary_key": primary_key,
            "foreign_keys": foreign_keys,
            "columns": columns,
        }

    def export_snapshot(self) -> dict[str, Any]:
        tables = {table: self.inspect_table(table) for table in self.list_tables()}
        return {
            "version": "generated_from_sqlite",
            "dialect": "sqlite",
            "database_path": str(self.db_path),
            "tables": tables,
        }

    def write_snapshot(self, output_path: str | Path = DEFAULT_SCHEMA_SNAPSHOT_PATH) -> Path:
        output = resolve_project_path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        snapshot = self.export_snapshot()
        output.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
        return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--out", default=str(DEFAULT_SCHEMA_SNAPSHOT_PATH))
    args = parser.parse_args()

    inspector = SQLiteSchemaInspector(args.db)
    output = inspector.write_snapshot(args.out)
    print(f"Schema snapshot written to: {output}")


if __name__ == "__main__":
    main()
