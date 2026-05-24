from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class SchemaLinkingResult:
    question: str
    normalized_question: str
    tables: list[str] = field(default_factory=list)
    columns: list[str] = field(default_factory=list)
    metrics: list[str] = field(default_factory=list)
    join_hints: list[str] = field(default_factory=list)
    schema_context: str = ""
    unresolved_terms: list[str] = field(default_factory=list)
    confidence: float = 0.0
    evidence: list[dict[str, Any]] = field(default_factory=list)

    def model_dump(self) -> dict[str, Any]:
        return asdict(self)

    def dict(self) -> dict[str, Any]:
        return asdict(self)


class SchemaLinker:
    """
    Defensive schema linker aligned with the current Phase-0 schema metadata.

    Key design choice:
    - Do not assume every value in metric_definitions.json is a metric spec.
    - Skip project/version/notes/meta fields safely.
    - Never return columns that do not exist in the frozen schema snapshot.
    """

    EXTRA_ALIASES: dict[str, list[str]] = {
        # Student depression dataset
        "افسردگی": [
            "student_depression.depression_flag",
            "mental_health_general.depression_score",
            "university_student_mental_health.depression_diagnosis",
            "country_prevalence_long.disorder",
            "country_prevalence_wide.depression_pct",
        ],
        "افسرده": ["student_depression.depression_flag"],
        "depressed": ["student_depression.depression_flag"],
        "depression": [
            "student_depression.depression_flag",
            "mental_health_general.depression_score",
            "country_prevalence_long.disorder",
            "country_prevalence_wide.depression_pct",
        ],
        "اضطراب": [
            "mental_health_general.anxiety_score",
            "university_student_mental_health.anxiety_diagnosis",
            "country_prevalence_long.disorder",
            "country_prevalence_wide.anxiety_pct",
        ],
        "anxiety": [
            "mental_health_general.anxiety_score",
            "country_prevalence_long.disorder",
            "country_prevalence_wide.anxiety_pct",
        ],
        "ezterab": ["mental_health_general.anxiety_score", "country_prevalence_long.disorder"],
        "معدل": ["student_depression.cgpa_10", "university_student_mental_health.cgpa_mid"],
        "cgpa": ["student_depression.cgpa_10", "university_student_mental_health.cgpa_mid"],
        "نمره امتحان": ["student_habits_performance.exam_score"],
        "exam score": ["student_habits_performance.exam_score"],
        "\u0633\u0627\u0639\u062a \u062e\u0648\u0627\u0628 \u062a\u0642\u0631\u06cc\u0628\u06cc": ["student_depression.sleep_mid_hours"],
        "\u062e\u0648\u0627\u0628 \u062a\u0642\u0631\u06cc\u0628\u06cc": ["student_depression.sleep_mid_hours"],
        "\u0634\u0628\u06a9\u0647 \u0627\u062c\u062a\u0645\u0627\u0639\u06cc": ["student_habits_performance.social_media_hours"],
        "\u0634\u0628\u06a9\u0647\u200c\u0647\u0627\u06cc \u0627\u062c\u062a\u0645\u0627\u0639\u06cc": ["student_habits_performance.social_media_hours"],
        "social media": ["student_habits_performance.social_media_hours"],
        "\u0631\u062a\u0628\u0647 \u0633\u0644\u0627\u0645\u062a \u0631\u0648\u0627\u0646": ["student_habits_performance.mental_health_rating"],
        "\u0646\u0645\u0631\u0647 \u0633\u0644\u0627\u0645\u062a \u0631\u0648\u0627\u0646": ["student_habits_performance.mental_health_rating"],
        "mental health rating": ["student_habits_performance.mental_health_rating"],
        "خواب": [
            "student_depression.sleep_mid_hours",
            "student_depression.sleep_duration_category",
            "mental_health_general.sleep_hours",
            "student_habits_performance.sleep_hours",
        ],
        "ساعت خواب": [
            "student_depression.sleep_mid_hours",
            "mental_health_general.sleep_hours",
            "student_habits_performance.sleep_hours",
        ],
        "جنسیت": [
            "student_depression.gender",
            "student_habits_performance.gender",
            "mental_health_general.gender",
            "university_student_mental_health.gender",
        ],
        "زن": [
            "student_depression.gender",
            "student_habits_performance.gender",
            "mental_health_general.gender",
            "university_student_mental_health.gender",
        ],
        "مرد": [
            "student_depression.gender",
            "student_habits_performance.gender",
            "mental_health_general.gender",
            "university_student_mental_health.gender",
        ],
        "gender": [
            "student_depression.gender",
            "student_habits_performance.gender",
            "mental_health_general.gender",
            "university_student_mental_health.gender",
        ],
        "دانشجو": ["student_depression.student_id", "student_habits_performance.student_id"],
        "دانشجوها": ["student_depression.student_id", "student_habits_performance.student_id"],
        "student": ["student_depression.student_id", "student_habits_performance.student_id"],
        "ریسک": ["mental_health_general.mental_health_risk"],
        "mental health risk": ["mental_health_general.mental_health_risk"],
        "درمان": ["mental_health_general.seeks_treatment", "workplace_mental_health_survey.treatment"],
        "treatment": ["mental_health_general.seeks_treatment", "workplace_mental_health_survey.treatment"],
        "کشور": ["country_prevalence_long.country_name", "country_prevalence_wide.country_name"],
        "سال": ["country_prevalence_long.year", "country_prevalence_wide.year"],
        "شیوع": ["country_prevalence_long.prevalence_pct"],
        "prevalence": ["country_prevalence_long.prevalence_pct"],
    }

    def __init__(self, project_root: str | Path | None = None) -> None:
        self.project_root = Path(project_root) if project_root else self._find_project_root()
        self.schema_dir = self.project_root / "data" / "schema"

        self.schema_snapshot = self._load_json("schema_snapshot.json")
        self.schema_graph = self._load_json("schema_graph.json")
        self.column_aliases = self._load_json("column_aliases.fa.json")
        self.business_glossary = self._load_json("business_glossary.fa.json")
        self.metric_definitions = self._load_json("metric_definitions.json")

        self.tables = self._extract_tables(self.schema_snapshot)
        self.valid_columns = self._build_valid_columns(self.tables)

    def _find_project_root(self) -> Path:
        current = Path(__file__).resolve()
        for parent in [current.parent, *current.parents]:
            if (parent / "data" / "schema").exists() and (parent / "src").exists():
                return parent
        return Path.cwd().resolve()

    def _load_json(self, filename: str) -> dict[str, Any]:
        path = self.schema_dir / filename
        if not path.exists():
            return {}
        import json

        return json.loads(path.read_text(encoding="utf-8"))

    def _extract_tables(self, snapshot: dict[str, Any]) -> dict[str, dict[str, Any]]:
        raw_tables = snapshot.get("tables", {})

        if isinstance(raw_tables, dict):
            return raw_tables

        if isinstance(raw_tables, list):
            result: dict[str, dict[str, Any]] = {}
            for table in raw_tables:
                if not isinstance(table, dict):
                    continue
                name = table.get("name")
                if not name:
                    continue

                cols: dict[str, dict[str, Any]] = {}
                for col in table.get("columns", []):
                    if isinstance(col, dict) and col.get("name"):
                        cols[col["name"]] = col

                result[name] = {**table, "columns": cols}
            return result

        return {}

    def _build_valid_columns(self, tables: dict[str, dict[str, Any]]) -> set[str]:
        values: set[str] = set()
        for table_name, table_info in tables.items():
            columns = table_info.get("columns", {})
            if isinstance(columns, dict):
                for column_name in columns:
                    values.add(f"{table_name}.{column_name}")
        return values

    def _normalize(self, text: str) -> str:
        try:
            from src.nlu.persian_normalizer import PersianNormalizer

            value = PersianNormalizer().normalize_text(text)
        except Exception:
            value = text

        try:
            from src.nlu.colloquial_mapper import ColloquialMapper

            value = ColloquialMapper().normalize(value).normalized
        except Exception:
            pass

        return value.strip().lower()

    def _contains(self, normalized_question: str, alias: str) -> bool:
        alias_norm = self._normalize(alias)
        if not alias_norm:
            return False
        if alias_norm in normalized_question:
            return True
        try:
            import rapidfuzz
            score = rapidfuzz.fuzz.partial_ratio(alias_norm, normalized_question)
            return score >= 85
        except ImportError:
            return False

    def _safe_add_column(
        self,
        columns: list[str],
        evidence: list[dict[str, Any]],
        fq_column: str,
        source: str,
        score: float = 0.85,
    ) -> None:
        if fq_column in self.valid_columns and fq_column not in columns:
            columns.append(fq_column)
            table = fq_column.split(".", 1)[0]
            evidence.append(
                {
                    "type": "column",
                    "value": fq_column,
                    "source": source,
                    "score": score,
                    "table": table,
                }
            )

    def _iter_alias_entries(self) -> list[tuple[str, list[str]]]:
        raw = self.column_aliases

        if isinstance(raw.get("aliases"), dict):
            raw = raw["aliases"]

        entries: list[tuple[str, list[str]]] = []

        if isinstance(raw, dict):
            for alias, targets in raw.items():
                if isinstance(targets, str):
                    targets = [targets]
                if isinstance(targets, list):
                    entries.append((str(alias), [str(x) for x in targets]))
        return entries

    def _iter_glossary_terms(self) -> list[tuple[str, dict[str, Any]]]:
        raw = self.business_glossary

        if isinstance(raw.get("terms"), dict):
            raw = raw["terms"]

        if not isinstance(raw, dict):
            return []

        terms: list[tuple[str, dict[str, Any]]] = []
        for term, spec in raw.items():
            if isinstance(spec, dict):
                terms.append((str(term), spec))
        return terms

    def _iter_metric_specs(self) -> list[tuple[str, dict[str, Any]]]:
        raw = self.metric_definitions

        # Support either {"metrics": {...}} or a direct metric dictionary.
        if isinstance(raw.get("metrics"), dict):
            raw = raw["metrics"]

        if not isinstance(raw, dict):
            return []

        specs: list[tuple[str, dict[str, Any]]] = []
        meta_keys = {
            "project",
            "artifact",
            "version",
            "created_at_utc",
            "generated_at_utc",
            "notes",
            "policy",
            "description",
        }

        for metric_name, spec in raw.items():
            if metric_name in meta_keys:
                continue
            if not isinstance(spec, dict):
                # Defensive fix: skip strings/lists/meta values.
                continue

            # A real metric usually has at least one of these keys.
            if not any(k in spec for k in ("sql_expression", "required_columns", "columns", "default_table", "aliases_fa", "aliases_en")):
                continue

            specs.append((str(metric_name), spec))

        return specs

    def _extract_columns_from_metric(self, spec: dict[str, Any]) -> list[str]:
        candidates: list[str] = []

        for key in ("required_columns", "columns", "preferred_columns"):
            value = spec.get(key)
            if isinstance(value, str):
                candidates.append(value)
            elif isinstance(value, list):
                candidates.extend(str(x) for x in value)

        # If the metric defines a default table and metric_column, combine them.
        table = spec.get("default_table")
        metric_column = spec.get("metric_column") or spec.get("column")
        if isinstance(table, str) and isinstance(metric_column, str):
            candidates.append(f"{table}.{metric_column}")

        return candidates

    def _make_schema_context(self, tables: list[str], columns: list[str]) -> str:
        lines: list[str] = []

        columns_by_table: dict[str, list[str]] = {}
        for fq_column in columns:
            table, col = fq_column.split(".", 1)
            columns_by_table.setdefault(table, []).append(col)

        for table_name in tables:
            table_info = self.tables.get(table_name, {})
            table_columns = table_info.get("columns", {})
            if not isinstance(table_columns, dict):
                continue

            row_count = table_info.get("row_count")
            header = f"TABLE {table_name}"
            if row_count is not None:
                header += f" -- rows: {row_count}"
            lines.append(header)

            selected_cols = columns_by_table.get(table_name) or list(table_columns.keys())[:6]
            for col in selected_cols:
                meta = table_columns.get(col, {})
                col_type = meta.get("type", "UNKNOWN") if isinstance(meta, dict) else "UNKNOWN"
                lines.append(f"  - {col} ({col_type})")

        return "\n".join(lines)

    def _join_hints_for_tables(self, tables: list[str]) -> list[str]:
        hints: list[str] = []
        table_set = set(tables)

        for edge in self.schema_graph.get("edges", []):
            if not isinstance(edge, dict):
                continue

            source = edge.get("source")
            target = edge.get("target")

            if source in table_set and target in table_set:
                join_sql = edge.get("join_sql")
                if join_sql:
                    hints.append(str(join_sql))

        return hints

    def link(self, question: str) -> SchemaLinkingResult:
        normalized = self._normalize(question)
        columns: list[str] = []
        metrics: list[str] = []
        evidence: list[dict[str, Any]] = []
        matched_aliases: list[str] = []

        try:
            from src.nlu.term_extractor import TermExtractor
            extractor = TermExtractor()
            extracted_terms = extractor.extract_terms(normalized)
        except Exception:
            extracted_terms = []

        # 1) Column aliases from metadata
        for alias, targets in self._iter_alias_entries():
            if self._contains(normalized, alias):
                matched_aliases.append(self._normalize(alias))
                for fq_column in targets:
                    self._safe_add_column(columns, evidence, fq_column, f"column_alias:{alias}", 1.0)

        # 2) Extra robust aliases for stress-test and common Persian/Finglish expressions
        for alias, targets in self.EXTRA_ALIASES.items():
            if self._contains(normalized, alias):
                matched_aliases.append(self._normalize(alias))
                for fq_column in targets:
                    self._safe_add_column(columns, evidence, fq_column, f"extra_alias:{alias}", 0.94)

        # 3) Business glossary preferred columns
        for term, spec in self._iter_glossary_terms():
            aliases = [term]
            for k in ("aliases_fa", "aliases_en", "synonyms_fa", "synonyms_en"):
                v = spec.get(k, [])
                if isinstance(v, str):
                    aliases.append(v)
                elif isinstance(v, list):
                    aliases.extend(str(x) for x in v)

            matched_any = False
            for alias in aliases:
                if self._contains(normalized, alias):
                    matched_aliases.append(self._normalize(alias))
                    matched_any = True
            
            if matched_any:
                preferred = spec.get("preferred_columns", [])
                if isinstance(preferred, str):
                    preferred = [preferred]
                if isinstance(preferred, list):
                    for fq_column in preferred:
                        self._safe_add_column(columns, evidence, str(fq_column), f"business_glossary:{term}", 0.92)

        # 4) Metrics
        for metric_name, spec in self._iter_metric_specs():
            aliases = [metric_name]
            for k in ("aliases_fa", "aliases_en", "synonyms_fa", "synonyms_en"):
                v = spec.get(k, [])
                if isinstance(v, str):
                    aliases.append(v)
                elif isinstance(v, list):
                    aliases.extend(str(x) for x in v)

            matched_any = False
            for alias in aliases:
                if self._contains(normalized, alias):
                    matched_aliases.append(self._normalize(alias))
                    matched_any = True

            if matched_any:
                if metric_name not in metrics:
                    metrics.append(metric_name)
                    evidence.append({"type": "metric", "value": metric_name, "source": "metric_definitions", "score": 0.9})
                for fq_column in self._extract_columns_from_metric(spec):
                    self._safe_add_column(columns, evidence, fq_column, f"metric:{metric_name}", 0.88)

        # 5) Direct column/table mention
        for fq_column in sorted(self.valid_columns):
            table, column = fq_column.split(".", 1)
            if column.lower() in normalized:
                matched_aliases.append(column.lower())
                self._safe_add_column(columns, evidence, fq_column, "direct_column_name", 0.75)

        if self._is_student_depression_dataset_context(normalized):
            columns = [col for col in columns if col.startswith("student_depression.")]
            evidence = [
                item
                for item in evidence
                if item.get("type") != "column" or str(item.get("value", "")).startswith("student_depression.")
            ]
            if not columns:
                for fq_column in (
                    "student_depression.student_depression_id",
                    "student_depression.age",
                    "student_depression.depression_flag",
                ):
                    self._safe_add_column(columns, evidence, fq_column, "dataset_context:student_depression", 0.96)
        elif self._is_general_mental_health_dataset_context(normalized):
            columns = [col for col in columns if col.startswith("mental_health_general.")]
            evidence = [
                item
                for item in evidence
                if item.get("type") != "column" or str(item.get("value", "")).startswith("mental_health_general.")
            ]
            if not columns:
                for fq_column in (
                    "mental_health_general.general_row_id",
                    "mental_health_general.depression_score",
                    "mental_health_general.anxiety_score",
                ):
                    self._safe_add_column(columns, evidence, fq_column, "dataset_context:mental_health_general", 0.96)

        tables: list[str] = []
        for fq_column in columns:
            table = fq_column.split(".", 1)[0]
            if table not in tables:
                tables.append(table)

        # If a metric references a default_table but no column was linked, add table.
        for metric_name, spec in self._iter_metric_specs():
            if metric_name in metrics:
                table = spec.get("default_table")
                if isinstance(table, str) and table in self.tables and table not in tables:
                    tables.append(table)

        join_hints = self._join_hints_for_tables(tables)
        schema_context = self._make_schema_context(tables, columns)

        confidence = 0.0
        if columns:
            confidence = min(1.0, 0.55 + 0.08 * len(columns) + 0.05 * len(metrics))

        # Calculate unresolved terms
        unresolved_terms: list[str] = []
        try:
            import rapidfuzz
            for term in extracted_terms:
                term_lower = term.lower()
                matched = False
                for alias in matched_aliases:
                    if term_lower in alias or rapidfuzz.fuzz.partial_ratio(term_lower, alias) >= 85:
                        matched = True
                        break
                if not matched:
                    unresolved_terms.append(term)
        except ImportError:
            unresolved_terms = extracted_terms

        return SchemaLinkingResult(
            question=question,
            normalized_question=normalized,
            tables=tables,
            columns=columns,
            metrics=metrics,
            join_hints=join_hints,
            schema_context=schema_context,
            unresolved_terms=unresolved_terms,
            confidence=round(confidence, 3),
            evidence=evidence,
        )

    def _is_student_depression_dataset_context(self, normalized: str) -> bool:
        dataset_terms = (
            "\u062f\u06cc\u062a\u0627\u0633\u062a",
            "\u062f\u0627\u062f\u0647",
            "\u062c\u062f\u0648\u0644",
            "dataset",
            "student_depression",
        )
        student_terms = (
            "\u062f\u0627\u0646\u0634\u062c\u0648\u06cc\u0627\u0646",
            "\u062f\u0627\u0646\u0634\u062c\u0648",
            "student",
        )
        depression_terms = (
            "\u0627\u0641\u0633\u0631\u062f\u06af\u06cc",
            "depression",
        )
        return (
            any(term in normalized for term in dataset_terms)
            and any(term in normalized for term in student_terms)
            and any(term in normalized for term in depression_terms)
        )

    def _is_general_mental_health_dataset_context(self, normalized: str) -> bool:
        dataset_terms = (
            "\u062f\u06cc\u062a\u0627\u0633\u062a",
            "\u062f\u0627\u062f\u0647",
            "\u062c\u062f\u0648\u0644",
            "dataset",
        )
        general_terms = (
            "\u0639\u0645\u0648\u0645\u06cc",
            "general",
            "mental_health_general",
        )
        mental_health_terms = (
            "\u0633\u0644\u0627\u0645\u062a \u0631\u0648\u0627\u0646",
            "\u0627\u0641\u0633\u0631\u062f\u06af\u06cc",
            "\u0627\u0636\u0637\u0631\u0627\u0628",
            "mental health",
            "depression",
            "anxiety",
        )
        return (
            any(term in normalized for term in dataset_terms)
            and any(term in normalized for term in general_terms)
            and any(term in normalized for term in mental_health_terms)
        )
