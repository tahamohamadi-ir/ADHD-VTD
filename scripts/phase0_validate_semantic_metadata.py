from __future__ import annotations

import sys

# Windows PowerShell/cp1252 safety: allow Persian/emoji output without UnicodeEncodeError.
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from _bootstrap_path import PROJECT_ROOT
except Exception:
    PROJECT_ROOT = Path(__file__).resolve().parents[1]


SCHEMA_PATH = PROJECT_ROOT / "data" / "schema" / "schema_snapshot.json"
SCHEMA_GRAPH_PATH = PROJECT_ROOT / "data" / "schema" / "schema_graph.json"
ALIASES_PATH = PROJECT_ROOT / "data" / "schema" / "column_aliases.fa.json"
GLOSSARY_PATH = PROJECT_ROOT / "data" / "schema" / "business_glossary.fa.json"
METRICS_PATH = PROJECT_ROOT / "data" / "schema" / "metric_definitions.json"
REPORT_PATH = PROJECT_ROOT / "data" / "audit" / "semantic_metadata_alignment_report.md"

FORBIDDEN_OLD_TABLES = {
    "individuals_core",
    "student_metrics",
    "clinical_assessments",
    "lifestyle_risk_factors",
    "global_benchmarks",
}


@dataclass
class CheckResult:
    name: str
    ok: bool
    message: str
    details: list[str] = field(default_factory=list)


def load_json(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def schema_map(schema: dict[str, Any]) -> dict[str, set[str]]:
    tables: dict[str, set[str]] = {}
    for table in schema.get("tables", []):
        name = table["name"]
        tables[name] = {col["name"] for col in table.get("columns", [])}
    return tables


def is_column_ref(value: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*", value))


def extract_column_refs(obj: Any, path: str = "") -> list[tuple[str, str]]:
    """
    Extract table.column references from nested JSON.
    Ignore values under forbidden_old_* keys because those intentionally document deprecated names.
    """
    refs: list[tuple[str, str]] = []

    if "forbidden_old" in path:
        return refs

    if isinstance(obj, dict):
        for key, value in obj.items():
            refs.extend(extract_column_refs(value, f"{path}.{key}" if path else key))
    elif isinstance(obj, list):
        for index, value in enumerate(obj):
            refs.extend(extract_column_refs(value, f"{path}[{index}]"))
    elif isinstance(obj, str):
        for ref in re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*)\b", obj):
            refs.append((path, ref))

    return refs


def validate_ref(ref: str, tables: dict[str, set[str]]) -> bool:
    if not is_column_ref(ref):
        return False
    table, column = ref.split(".", 1)
    return table in tables and column in tables[table]


def validate_no_old_tables_in_active_content(obj: Any, artifact_name: str) -> CheckResult:
    hits: list[str] = []

    def walk(x: Any, path: str = "") -> None:
        if "forbidden_old" in path or "deprecated" in path:
            return
        if isinstance(x, dict):
            for k, v in x.items():
                walk(v, f"{path}.{k}" if path else k)
        elif isinstance(x, list):
            for i, v in enumerate(x):
                walk(v, f"{path}[{i}]")
        elif isinstance(x, str):
            for old in FORBIDDEN_OLD_TABLES:
                if old in x:
                    hits.append(f"{path}: {old}")

    walk(obj)

    return CheckResult(
        name=f"{artifact_name}: no active old-table references",
        ok=not hits,
        message="No old table names found in active metadata." if not hits else "Old table names found in active metadata.",
        details=hits,
    )


def validate_aliases(aliases: dict[str, Any], tables: dict[str, set[str]]) -> CheckResult:
    errors: list[str] = []
    for alias, refs in aliases.items():
        if not isinstance(refs, list) or not refs:
            errors.append(f"{alias}: expected non-empty list of table.column refs")
            continue
        for ref in refs:
            if not validate_ref(ref, tables):
                errors.append(f"{alias} -> {ref}")
    return CheckResult(
        name="column_aliases.fa.json references current schema",
        ok=not errors,
        message="All alias references resolve to current schema." if not errors else "Invalid alias references found.",
        details=errors,
    )


def validate_schema_graph(graph: dict[str, Any], tables: dict[str, set[str]]) -> list[CheckResult]:
    results: list[CheckResult] = []

    node_ids = [node.get("id") for node in graph.get("nodes", [])]
    missing_nodes = [node_id for node_id in node_ids if node_id not in tables]
    results.append(CheckResult(
        name="schema_graph nodes are current tables",
        ok=not missing_nodes,
        message="All graph nodes are real current tables." if not missing_nodes else "Some graph nodes are not in schema.",
        details=missing_nodes,
    ))

    edge_errors: list[str] = []
    for edge in graph.get("edges", []):
        source = edge.get("source")
        target = edge.get("target")
        if source not in tables:
            edge_errors.append(f"edge {edge.get('id')}: source table missing: {source}")
            continue
        if target not in tables:
            edge_errors.append(f"edge {edge.get('id')}: target table missing: {target}")
            continue
        for col in edge.get("source_columns", []):
            if col not in tables[source]:
                edge_errors.append(f"edge {edge.get('id')}: source column missing: {source}.{col}")
        for col in edge.get("target_columns", []):
            if col not in tables[target]:
                edge_errors.append(f"edge {edge.get('id')}: target column missing: {target}.{col}")

    results.append(CheckResult(
        name="schema_graph edges reference valid tables/columns",
        ok=not edge_errors,
        message="All graph edges reference current schema." if not edge_errors else "Invalid graph edges found.",
        details=edge_errors,
    ))

    return results


def validate_recursive_refs(obj: Any, artifact_name: str, tables: dict[str, set[str]]) -> CheckResult:
    errors = []
    for path, ref in extract_column_refs(obj):
        if not validate_ref(ref, tables):
            errors.append(f"{path}: {ref}")
    return CheckResult(
        name=f"{artifact_name}: embedded table.column refs",
        ok=not errors,
        message="All embedded table.column refs resolve." if not errors else "Invalid embedded table.column refs found.",
        details=errors,
    )


def validate_metrics(metrics: dict[str, Any], tables: dict[str, set[str]]) -> CheckResult:
    errors: list[str] = []
    metric_defs = metrics.get("metrics", {})
    if not isinstance(metric_defs, dict) or not metric_defs:
        errors.append("metrics.metrics must be a non-empty object")
    for metric_name, metric in metric_defs.items():
        table = metric.get("default_table")
        if table not in tables:
            errors.append(f"{metric_name}: default_table missing: {table}")
        for ref in metric.get("required_columns", []):
            if not validate_ref(ref, tables):
                errors.append(f"{metric_name}: invalid required column: {ref}")
    return CheckResult(
        name="metric_definitions.json metric contracts",
        ok=not errors,
        message="All metrics reference current tables/columns." if not errors else "Invalid metric definitions found.",
        details=errors,
    )


def write_report(results: list[CheckResult], schema: dict[str, Any]) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    ok_count = sum(1 for r in results if r.ok)
    fail_count = len(results) - ok_count
    table_count = len(schema.get("tables", []))
    old_refs = ", ".join(sorted(FORBIDDEN_OLD_TABLES))

    lines = [
        "# Semantic Metadata Alignment Report",
        "",
        f"**Generated at UTC:** {datetime.now(timezone.utc).isoformat()}",
        f"**Schema file:** `{SCHEMA_PATH.relative_to(PROJECT_ROOT)}`",
        f"**Current table count:** {table_count}",
        f"**Checks passed:** {ok_count}/{len(results)}",
        f"**Checks failed:** {fail_count}",
        "",
        "## Current Schema Tables",
        "",
    ]

    for table in schema.get("tables", []):
        lines.append(f"- `{table['name']}` ({len(table.get('columns', []))} columns)")

    lines += [
        "",
        "## Forbidden Old Tables",
        "",
        f"The following old schema names must not appear in active metadata: `{old_refs}`.",
        "",
        "## Check Results",
        "",
        "| Check | Status | Message |",
        "|---|---|---|",
    ]

    for result in results:
        status = "✅ PASS" if result.ok else "❌ FAIL"
        lines.append(f"| {result.name} | {status} | {result.message} |")

    failures = [r for r in results if not r.ok]
    if failures:
        lines += ["", "## Failure Details", ""]
        for result in failures:
            lines.append(f"### {result.name}")
            for detail in result.details[:200]:
                lines.append(f"- `{detail}`")
            if len(result.details) > 200:
                lines.append(f"- ... {len(result.details) - 200} more")
            lines.append("")
    else:
        lines += [
            "",
            "## Decision",
            "",
            "✅ Semantic metadata is aligned with the current schema.",
            "",
            "You may proceed to implement:",
            "",
            "- `src/schema/value_linker.py`",
            "- `src/nlu/intent_classifier.py`",
            "- `src/nlu/ambiguity_detector.py`",
            "- `src/nlu/safety_intent_detector.py`",
            "- `src/sql_validation/safety_validator.py`",
            "- `src/sql_validation/syntax_validator.py`",
        ]

    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    schema = load_json(SCHEMA_PATH)
    tables = schema_map(schema)

    graph = load_json(SCHEMA_GRAPH_PATH)
    aliases = load_json(ALIASES_PATH)
    glossary = load_json(GLOSSARY_PATH)
    metrics = load_json(METRICS_PATH)

    results: list[CheckResult] = []

    results.extend(validate_schema_graph(graph, tables))
    results.append(validate_aliases(aliases, tables))
    results.append(validate_recursive_refs(graph, "schema_graph.json", tables))
    results.append(validate_recursive_refs(glossary, "business_glossary.fa.json", tables))
    results.append(validate_recursive_refs(metrics, "metric_definitions.json", tables))
    results.append(validate_metrics(metrics, tables))

    results.append(validate_no_old_tables_in_active_content(graph, "schema_graph.json"))
    results.append(validate_no_old_tables_in_active_content(aliases, "column_aliases.fa.json"))
    results.append(validate_no_old_tables_in_active_content(glossary, "business_glossary.fa.json"))
    results.append(validate_no_old_tables_in_active_content(metrics, "metric_definitions.json"))

    write_report(results, schema)

    failed = [r for r in results if not r.ok]
    print(f"Semantic metadata checks: {len(results) - len(failed)}/{len(results)} passed")
    print(f"Report written to: {REPORT_PATH}")
    if failed:
        for result in failed:
            print(f"[FAIL] {result.name}: {result.message}")
            for detail in result.details[:20]:
                print(f"  - {detail}")
        return 1

    print("✅ Semantic metadata is aligned with current schema.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
