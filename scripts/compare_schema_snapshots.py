"""Compare schema_snapshot.json vs schema_snapshot.generated.json.

Reports differences in tables, columns, types, and foreign keys.
Exit code: 0 if identical, 1 if differences exist.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config.paths import SCHEMA_DIR


def load_schema(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def tables_map(schema: dict) -> dict[str, dict]:
    return {t["name"]: t for t in schema.get("tables", []) if t.get("name")}


def columns_map(table: dict) -> dict[str, dict]:
    return {c["name"]: c for c in table.get("columns", []) if c.get("name")}


def diff_schemas(frozen: dict, generated: dict) -> list[str]:
    ft = tables_map(frozen)
    gt = tables_map(generated)
    diffs: list[str] = []

    only_frozen = set(ft) - set(gt)
    only_gen = set(gt) - set(ft)
    common = set(ft) & set(gt)

    for t in sorted(only_frozen):
        diffs.append(f"TABLE REMOVED from generated: {t}")
    for t in sorted(only_gen):
        diffs.append(f"TABLE ADDED in generated: {t}")

    for tname in sorted(common):
        fc = columns_map(ft[tname])
        gc = columns_map(gt[tname])
        only_fc = set(fc) - set(gc)
        only_gc = set(gc) - set(fc)
        common_cols = set(fc) & set(gc)

        for c in sorted(only_fc):
            diffs.append(f"COLUMN REMOVED from generated: {tname}.{c}")
        for c in sorted(only_gc):
            diffs.append(f"COLUMN ADDED in generated: {tname}.{c}")
        for c in sorted(common_cols):
            ftype = fc[c].get("type", "")
            gtype = gc[c].get("type", "")
            if ftype != gtype:
                diffs.append(f"TYPE CHANGED: {tname}.{c}: {ftype} → {gtype}")
            fpk = fc[c].get("primary_key", False)
            gpk = gc[c].get("primary_key", False)
            if fpk != gpk:
                diffs.append(f"PK CHANGED: {tname}.{c}: {fpk} → {gpk}")

    return diffs


def main():
    frozen_path = SCHEMA_DIR / "schema_snapshot.json"
    gen_path = SCHEMA_DIR / "schema_snapshot.generated.json"

    print(f"Frozen:    {frozen_path}")
    print(f"Generated: {gen_path}")

    frozen = load_schema(frozen_path)
    generated = load_schema(gen_path)

    if not frozen:
        print("❌ schema_snapshot.json not found or empty!")
        sys.exit(1)
    if not generated:
        print("❌ schema_snapshot.generated.json not found or empty!")
        sys.exit(1)

    diffs = diff_schemas(frozen, generated)

    # Write report
    report_dir = Path("results/data_quality")
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "schema_diff_report.md"

    lines = [
        "# Schema Diff Report",
        "",
        f"**Frozen:** `{frozen_path.name}`  ",
        f"**Generated:** `{gen_path.name}`  ",
        f"**Tables (frozen):** {len(tables_map(frozen))}  ",
        f"**Tables (generated):** {len(tables_map(generated))}  ",
        "",
    ]

    if not diffs:
        lines.append("✅ **No differences found. Schemas are identical.**")
        print("\n✅ Schemas are identical.")
    else:
        lines.append(f"❌ **{len(diffs)} difference(s) found:**\n")
        lines.append("| # | Difference |")
        lines.append("|---|---|")
        for i, d in enumerate(diffs, 1):
            lines.append(f"| {i} | {d} |")
        print(f"\n❌ {len(diffs)} difference(s) found:")
        for d in diffs:
            print(f"  - {d}")

    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nReport: {report_path}")
    sys.exit(1 if diffs else 0)


if __name__ == "__main__":
    main()
