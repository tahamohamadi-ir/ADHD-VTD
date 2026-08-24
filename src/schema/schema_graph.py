from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

try:
    from src.config.paths import SCHEMA_GRAPH_PATH, SCHEMA_SNAPSHOT_PATH
except Exception:  # pragma: no cover
    SCHEMA_GRAPH_PATH = Path("data/schema/schema_graph.json")
    SCHEMA_SNAPSHOT_PATH = Path("data/schema/schema_snapshot.json")


@dataclass(frozen=True)
class GraphEdge:
    source: str
    target: str
    source_columns: list[str]
    target_columns: list[str]
    join_sql: str | None
    confidence: str = "manual"


@dataclass
class SchemaGraphModel:
    tables: set[str] = field(default_factory=set)
    edges: list[GraphEdge] = field(default_factory=list)
    domains: dict[str, dict] = field(default_factory=dict)


class SchemaGraph:
    """Schema graph with no fake joins. Cross-table joins are opt-in/manual only."""

    def __init__(
        self, graph_path: str | Path | None = None, snapshot_path: str | Path | None = None
    ) -> None:
        self.graph_path = Path(graph_path or SCHEMA_GRAPH_PATH)
        self.snapshot_path = Path(snapshot_path or SCHEMA_SNAPSHOT_PATH)
        self.model = self._load()

    def _load_json(self, path: Path) -> dict:
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    def _load(self) -> SchemaGraphModel:
        graph = self._load_json(self.graph_path)
        snapshot = self._load_json(self.snapshot_path)
        tables = {t.get("name") for t in snapshot.get("tables", []) if t.get("name")}
        for node in graph.get("nodes", []):
            if node.get("id"):
                tables.add(node["id"])
        domains = {n.get("id"): n for n in graph.get("nodes", []) if n.get("id")}
        edges: list[GraphEdge] = []
        for e in graph.get("edges", []):
            source_cols = e.get("source_columns") or (
                [e.get("source_column")] if e.get("source_column") else []
            )
            target_cols = e.get("target_columns") or (
                [e.get("target_column")] if e.get("target_column") else []
            )
            edges.append(
                GraphEdge(
                    source=e.get("source"),
                    target=e.get("target"),
                    source_columns=[c for c in source_cols if c],
                    target_columns=[c for c in target_cols if c],
                    join_sql=e.get("join_sql"),
                    confidence=e.get("confidence", "manual"),
                )
            )
        return SchemaGraphModel(tables={t for t in tables if t}, edges=edges, domains=domains)

    def has_table(self, table: str) -> bool:
        return table in self.model.tables

    def direct_edges(self, table: str) -> list[GraphEdge]:
        return [e for e in self.model.edges if e.source == table or e.target == table]

    def find_direct_join(self, left: str, right: str) -> GraphEdge | None:
        for e in self.model.edges:
            if {e.source, e.target} == {left, right}:
                return e
        return None
