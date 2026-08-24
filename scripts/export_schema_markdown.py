"""Export schema as markdown reference from schema_snapshot.json."""

from __future__ import annotations
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config.paths import SCHEMA_DIR

SCHEMA_PATH = SCHEMA_DIR / "schema_snapshot.json"
GRAPH_PATH = SCHEMA_DIR / "schema_graph.json"
OUTPUT = Path("docs/generated/SCHEMA_REFERENCE.md")


def main():
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    tables = schema.get("tables", [])
    graph = json.loads(GRAPH_PATH.read_text(encoding="utf-8")) if GRAPH_PATH.exists() else {}
    edges = graph.get("edges", [])
    lines = ["# VTD Schema Reference", "", f"> Tables: {len(tables)}", ""]
    for t in tables:
        nm = t["name"]
        rc = t.get("row_count", "?")
        cols = t.get("columns", [])
        lines += [f"## {nm}", f"**Rows:** {rc}", "", "| Column | Type | PK |", "|---|---|---|"]
        for c in cols:
            pk = "✅" if c.get("primary_key") else ""
            lines.append(f"| `{c['name']}` | {c.get('type', '?')} | {pk} |")
        te = [e for e in edges if e.get("from_table") == nm or e.get("to_table") == nm]
        if te:
            lines.append("\n**Relations:**")
            for e in te:
                lines.append(
                    f"- `{e['from_table']}.{e['from_column']}` → `{e['to_table']}.{e['to_column']}`"
                )
        lines.append("\n---\n")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text("\n".join(lines), encoding="utf-8")
    print(
        f"✅ {OUTPUT} — {len(tables)} tables, {sum(len(t.get('columns', [])) for t in tables)} columns"
    )


if __name__ == "__main__":
    main()
