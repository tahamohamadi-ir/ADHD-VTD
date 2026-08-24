from __future__ import annotations

import json
from pathlib import Path

try:
    from src.config.paths import SCHEMA_DIR
except Exception:  # pragma: no cover
    SCHEMA_DIR = Path("data/schema")


class BusinessRules:
    """Access domain-specific routing, metric, and glossary rules."""

    def __init__(self, schema_dir: str | Path | None = None) -> None:
        self.schema_dir = Path(schema_dir or SCHEMA_DIR)
        self.glossary = self._load("business_glossary.fa.json")
        self.metrics = self._load("metric_definitions.json")
        self.aliases = self._load("column_aliases.fa.json")

    def _load(self, name: str) -> dict:
        path = self.schema_dir / name
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    def aliases_for(self, term: str) -> list[str]:
        return list(self.aliases.get(term, []))

    def metric(self, metric_name: str) -> dict | None:
        return self.metrics.get(metric_name)

    def all_metric_names(self) -> list[str]:
        return sorted(self.metrics)

    def glossary_term(self, term: str) -> dict | None:
        return self.glossary.get(term)
