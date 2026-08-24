from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

NA = "n/a"
HASH_SHORT_LENGTH = 16
_HEX_RE = re.compile(r"[0-9a-f]+")
_FRACTION_STRING_RE = re.compile(r"^\s*(\d+)\s*/\s*(\d+)\s*(?:=\s*([0-9.]+))?\s*$")

PROMOTION_REQUIRED_COLUMNS = frozenset(
    {
        "scope",
        "artifact_type",
        "artifact_path",
        "evidence_family",
        "status",
        "paper_metric_allowed",
    }
)
PROMOTION_ALLOWED_STATUSES = frozenset({"paper_final", "diagnostic_only", "pending_review"})
PROMOTION_ALLOWED_TYPES = frozenset({"benchmark", "judge"})
PROMOTION_ALLOWED_FAMILIES = frozenset({"sql_positive", "semantic_business", "behavioral"})
FINAL_FORBIDDEN_SUBSTRINGS = (
    "smoke",
    "dryrun",
    "dry_run",
    "diagnostic",
    "shadow",
    "mock",
    "pending",
    "provider_error",
    "failed",
)
FINAL_FORBIDDEN_SPL_RE = re.compile(r"(^|[/_-])spl\d+($|[/_-])")
TRUE_VALUES = frozenset({"true", "yes", "1"})
FALSE_VALUES = frozenset({"false", "no", "0"})

REPORTING_CONSTRAINTS: tuple[str, ...] = (
    "Report strict execution accuracy, behavioral expected-action accuracy, and "
    "semantic/business judge accuracy separately.",
    "Do not cite smoke, dry-run, mock, shadow, SPL, failed, provider-error, or "
    "pending-review artifacts as final paper metrics.",
    "Every reported number traces to the artifact directory listed beside it and to "
    "the promotion registry.",
    "Diagnostic evidence stays out of the paper-facing tables unless explicitly "
    "included, and is never paper-final.",
)


def parse_promotion_bool(value: str) -> bool | None:
    normalized = value.strip().lower()
    if normalized in TRUE_VALUES:
        return True
    if normalized in FALSE_VALUES:
        return False
    return None


def has_forbidden_final_marker(normalized_path: str) -> bool:
    lowered = normalized_path.replace("\\", "/").lower()
    return any(marker in lowered for marker in FINAL_FORBIDDEN_SUBSTRINGS) or bool(
        FINAL_FORBIDDEN_SPL_RE.search(lowered)
    )


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def normalize_artifact_path_value(value: str) -> str:
    return value.strip().strip("`").replace("\\", "/").strip().lower()


def _looks_like_markdown_table_row(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith("|") and stripped.endswith("|")


def _looks_like_markdown_separator(line: str) -> bool:
    if not _looks_like_markdown_table_row(line):
        return False
    cells = _split_markdown_row(line)
    return bool(cells) and all(set(cell.strip()) <= {"-", ":"} for cell in cells)


def _split_markdown_row(line: str) -> list[str]:
    stripped = line.strip().strip("|")
    return [cell.strip() for cell in stripped.split("|")]


def _normalize_table_cell(value: str) -> str:
    return value.strip().strip("`").strip()


def _normalize_column_name(value: str) -> str:
    normalized = value.lower().replace("-", "_").replace(" ", "_")
    return "_".join(part for part in normalized.split("_") if part)


def parse_promotion_registry(text: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if not _looks_like_markdown_table_row(line):
            continue
        headers = [_normalize_table_cell(cell) for cell in _split_markdown_row(line)]
        normalized_headers = [_normalize_column_name(header) for header in headers]
        if not PROMOTION_REQUIRED_COLUMNS.issubset(set(normalized_headers)):
            continue
        if index + 1 >= len(lines) or not _looks_like_markdown_separator(lines[index + 1]):
            continue
        column_indexes = {header: position for position, header in enumerate(normalized_headers)}
        ordered_columns = sorted(PROMOTION_REQUIRED_COLUMNS)
        row_index = index + 2
        while row_index < len(lines) and _looks_like_markdown_table_row(lines[row_index]):
            cells = [_normalize_table_cell(cell) for cell in _split_markdown_row(lines[row_index])]
            if cells:
                rows.append(
                    {
                        column: (
                            cells[column_indexes[column]]
                            if column_indexes[column] < len(cells)
                            else ""
                        )
                        for column in ordered_columns
                    }
                )
            row_index += 1
    return rows


def _promotion_table_row_map(text: str) -> dict[int, tuple[int, dict[str, int]]]:
    mapping: dict[int, tuple[int, dict[str, int]]] = {}
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if not _looks_like_markdown_table_row(line):
            continue
        headers = [_normalize_table_cell(cell) for cell in _split_markdown_row(line)]
        normalized_headers = [_normalize_column_name(header) for header in headers]
        if not PROMOTION_REQUIRED_COLUMNS.issubset(set(normalized_headers)):
            continue
        if index + 1 >= len(lines) or not _looks_like_markdown_separator(lines[index + 1]):
            continue
        column_indexes = {header: position for position, header in enumerate(normalized_headers)}
        row_index = index + 2
        while row_index < len(lines) and _looks_like_markdown_table_row(lines[row_index]):
            mapping[row_index] = (index, column_indexes)
            row_index += 1
    return mapping


def _rewrite_row_cells(line: str, replacements: Mapping[int, str]) -> str:
    segments = re.split(r"(\|)", line)
    for column, new_value in replacements.items():
        segment_index = 2 * column + 2
        if segment_index >= len(segments):
            raise ValueError(f"Promotion row column index {column} is out of range.")
        segments[segment_index] = f" {new_value} "
    return "".join(segments)


def set_promotion_status(
    doc_text: str,
    *,
    artifact_path: str,
    new_status: str,
    paper_metric_allowed: bool,
) -> str:
    if new_status not in PROMOTION_ALLOWED_STATUSES:
        allowed = ", ".join(sorted(PROMOTION_ALLOWED_STATUSES))
        raise ValueError(f"Invalid promotion status {new_status!r}. Allowed: {allowed}.")
    if paper_metric_allowed and new_status in {"diagnostic_only", "pending_review"}:
        raise ValueError(
            f"Status {new_status!r} cannot allow paper metrics; "
            "use status=paper_final for metric promotion."
        )
    target = normalize_artifact_path_value(artifact_path)
    if not target or target in {"-", "n/a"}:
        raise ValueError("artifact_path must identify a registered artifact directory.")
    lines = doc_text.splitlines()
    row_map = _promotion_table_row_map(doc_text)
    matches: list[tuple[int, dict[str, int]]] = []
    for line_no, (_, column_indexes) in row_map.items():
        cells = [_normalize_table_cell(cell) for cell in _split_markdown_row(lines[line_no])]
        normalized_cells = [normalize_artifact_path_value(cell) for cell in cells]
        if target in normalized_cells:
            matches.append((line_no, column_indexes))
    if not matches:
        raise ValueError(f"No promotion registry row references artifact path {artifact_path!r}.")
    if len(matches) > 1:
        raise ValueError(
            f"Ambiguous promotion registry edit: {len(matches)} rows reference "
            f"artifact path {artifact_path!r}."
        )
    line_no, column_indexes = matches[0]
    replacements = {
        column_indexes["status"]: new_status,
        column_indexes["paper_metric_allowed"]: "true" if paper_metric_allowed else "false",
    }
    updated_lines = list(lines)
    updated_lines[line_no] = _rewrite_row_cells(updated_lines[line_no], replacements)
    newline = "\r\n" if "\r\n" in doc_text else "\n"
    suffix = newline if doc_text.endswith(("\n", "\r\n")) else ""
    return newline.join(updated_lines) + suffix


@dataclass(frozen=True, slots=True)
class PromotionRow:
    scope: str
    artifact_type: str
    artifact_path: str
    evidence_family: str
    status: str
    paper_metric_allowed_raw: str
    notes: str = ""

    @classmethod
    def from_cells(cls, cells: Mapping[str, str]) -> PromotionRow:
        return cls(
            scope=cells.get("scope", "").strip(),
            artifact_type=cells.get("artifact_type", "").strip().lower(),
            artifact_path=cells.get("artifact_path", "").strip(),
            evidence_family=cells.get("evidence_family", "").strip().lower(),
            status=cells.get("status", "").strip().lower(),
            paper_metric_allowed_raw=cells.get("paper_metric_allowed", "").strip(),
            notes=cells.get("notes", "").strip(),
        )

    @property
    def normalized_artifact_path(self) -> str:
        return normalize_artifact_path_value(self.artifact_path)

    @property
    def paper_metric_allowed(self) -> bool | None:
        return parse_promotion_bool(self.paper_metric_allowed_raw)

    @property
    def is_paper_final(self) -> bool:
        return self.status == "paper_final"

    @property
    def has_forbidden_final_marker(self) -> bool:
        return has_forbidden_final_marker(self.normalized_artifact_path)

    def validation_errors(self) -> tuple[str, ...]:
        errors: list[str] = []
        if self.status not in PROMOTION_ALLOWED_STATUSES:
            errors.append(f"invalid status {self.status!r}")
        if self.artifact_type not in PROMOTION_ALLOWED_TYPES:
            errors.append(f"invalid artifact_type {self.artifact_type!r}")
        if self.evidence_family not in PROMOTION_ALLOWED_FAMILIES:
            errors.append(f"invalid evidence_family {self.evidence_family!r}")
        allowed = self.paper_metric_allowed
        if allowed is None:
            errors.append("paper_metric_allowed must be true/false, yes/no, or 1/0")
        elif not self.is_paper_final and allowed:
            errors.append(f"status {self.status!r} cannot allow paper metrics")
        if self.artifact_type == "judge" and self.evidence_family != "semantic_business":
            errors.append("judge artifacts must be registered as semantic_business")
        if self.artifact_type == "benchmark" and self.evidence_family == "semantic_business":
            errors.append("semantic/business evidence cannot come from benchmark artifacts")
        return tuple(errors)


@dataclass(frozen=True, slots=True)
class ScopeEvaluation:
    row: PromotionRow
    included: bool
    exclusion_reason: str = ""
    verification_ok: bool | None = None
    verification_issues: tuple[str, ...] = ()
    metrics: dict[str, str] = field(default_factory=dict)
    provenance: dict[str, str] = field(default_factory=dict)

    @property
    def scope(self) -> str:
        return self.row.scope

    @property
    def evidence_family(self) -> str:
        return self.row.evidence_family

    @property
    def is_diagnostic(self) -> bool:
        return not self.row.is_paper_final


def resolve_artifact_path(raw_path: str, root: Path) -> Path:
    candidate = Path(raw_path)
    if candidate.is_absolute():
        return candidate
    return root / Path(raw_path.replace("\\", "/"))


def verify_benchmark_artifact(artifact_dir: Path) -> tuple[bool, tuple[str, ...]]:
    from scripts.verify_artifact import verify_artifact

    report = verify_artifact(artifact_dir)
    issues = tuple(f"{issue.code}: {issue.message}" for issue in report.issues)
    return report.ok, issues


def verify_judge_artifact(artifact_dir: Path) -> tuple[bool, tuple[str, ...]]:
    from src.evaluation.llm_judge import validate_judge_artifact

    report = validate_judge_artifact(artifact_dir, require_authoritative=True)
    issues = tuple(f"{issue.code}: {issue.message}" for issue in report.issues)
    return report.ok, issues


def deep_verify_scope(row: PromotionRow, root: Path) -> tuple[bool, tuple[str, ...]]:
    artifact_dir = resolve_artifact_path(row.artifact_path, root)
    if row.artifact_type == "benchmark":
        return verify_benchmark_artifact(artifact_dir)
    if row.artifact_type == "judge":
        return verify_judge_artifact(artifact_dir)
    return False, (f"unsupported artifact_type {row.artifact_type!r}",)


def find_benchmark_summary_path(artifact_dir: Path) -> Path | None:
    if not artifact_dir.is_dir():
        return None
    candidates = sorted(
        path for path in artifact_dir.glob("*_summary.json") if "_partial_" not in path.name
    )
    if candidates:
        return candidates[0]
    plain = artifact_dir / "summary.json"
    return plain if plain.exists() else None


def load_json_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def load_scope_summary(row: PromotionRow, artifact_dir: Path) -> dict[str, Any]:
    if row.artifact_type == "judge":
        path = artifact_dir / "judge_summary.json"
    else:
        path = find_benchmark_summary_path(artifact_dir)
    if path is None:
        return {}
    return load_json_object(path)


def _text_or_na(value: Any) -> str:
    if value is None:
        return NA
    text = str(value).strip()
    return text if text else NA


def _int_or_na(value: Any) -> str:
    if isinstance(value, bool) or not isinstance(value, int):
        return NA
    return str(value)


def _number_or_na(value: Any) -> str:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return NA
    return f"{value:g}"


def _bool_or_na(value: Any) -> str:
    if not isinstance(value, bool):
        return NA
    return "true" if value else "false"


def _fraction_or_na(numerator: Any, denominator: Any, value: Any = None) -> str:
    if not isinstance(numerator, int) or isinstance(numerator, bool):
        return NA
    if not isinstance(denominator, int) or isinstance(denominator, bool) or denominator <= 0:
        return str(numerator)
    ratio = (
        float(value)
        if isinstance(value, (int, float)) and not isinstance(value, bool)
        else numerator / denominator
    )
    return f"{numerator}/{denominator}={ratio:.4f}"


def _render_metric_value(entry: Any) -> str:
    if isinstance(entry, Mapping):
        numerator = entry.get("numerator")
        denominator = entry.get("denominator")
        value = entry.get("value")
        if isinstance(numerator, int) and not isinstance(numerator, bool):
            fraction = _fraction_or_na(numerator, denominator, value)
            if fraction != NA:
                return fraction
        return _number_or_na(value) if value is not None else NA
    if isinstance(entry, str):
        match = _FRACTION_STRING_RE.match(entry)
        if match:
            numerator = int(match.group(1))
            denominator = int(match.group(2))
            value = float(match.group(3)) if match.group(3) else None
            return _fraction_or_na(numerator, denominator, value)
        return entry.strip() if entry.strip() else NA
    if isinstance(entry, bool) or entry is None:
        return NA
    if isinstance(entry, int):
        return str(entry)
    if isinstance(entry, float):
        return f"{entry:.4f}"
    return _number_or_na(entry)


def extract_benchmark_metrics(summary: Mapping[str, Any]) -> dict[str, str]:
    metrics = summary.get("metrics") if isinstance(summary.get("metrics"), Mapping) else {}
    latency = summary.get("latency") if isinstance(summary.get("latency"), Mapping) else {}
    reliability = (
        summary.get("reliability") if isinstance(summary.get("reliability"), Mapping) else {}
    )
    errors = (
        summary.get("error_analysis") if isinstance(summary.get("error_analysis"), Mapping) else {}
    )
    dataset = summary.get("dataset") if isinstance(summary.get("dataset"), Mapping) else {}
    config = summary.get("config") if isinstance(summary.get("config"), Mapping) else {}
    module_flags = (
        config.get("module_flags") if isinstance(config.get("module_flags"), Mapping) else {}
    )

    def metric(name: str) -> str:
        return _render_metric_value(metrics.get(name))

    return {
        "total_evaluated": _int_or_na(dataset.get("total_evaluated")),
        "execution_accuracy": metric("execution_accuracy"),
        "valid_sql_rate": metric("valid_sql_rate"),
        "expected_action_accuracy": metric("expected_action_accuracy"),
        "clarification_accuracy": metric("clarification_accuracy"),
        "safety_rejection_accuracy": metric("safety_rejection_accuracy"),
        "abstention_precision": metric("abstention_precision"),
        "abstention_recall": metric("abstention_recall"),
        "failures": _int_or_na(errors.get("total_errors")),
        "unsafe_sql": _int_or_na(reliability.get("unsafe_sql")),
        "reliability_score": _number_or_na(reliability.get("score")),
        "mean_latency_ms": _number_or_na(latency.get("mean_ms")),
        "p95_latency_ms": _number_or_na(latency.get("p95_ms")),
        "deterministic_templates": _bool_or_na(module_flags.get("deterministic_templates")),
        "max_retries": _int_or_na(config.get("max_retries")),
    }


def extract_judge_metrics(summary: Mapping[str, Any]) -> dict[str, str]:
    verdicts = (
        summary.get("verdict_counts") if isinstance(summary.get("verdict_counts"), Mapping) else {}
    )
    counts = (
        summary.get("semantic_business_counts")
        if isinstance(summary.get("semantic_business_counts"), Mapping)
        else {}
    )
    redaction = (
        summary.get("redaction_policy")
        if isinstance(summary.get("redaction_policy"), Mapping)
        else {}
    )
    total_judged = summary.get("total_judged")
    correct = counts.get("correct", verdicts.get("business_correct"))
    incorrect = counts.get("incorrect", verdicts.get("business_incorrect"))
    return {
        "provider": _text_or_na(summary.get("provider")),
        "model": _text_or_na(summary.get("model")),
        "prompt_version": _text_or_na(summary.get("prompt_version")),
        "judge_policy": _text_or_na(summary.get("judge_policy")),
        "authoritative": _bool_or_na(summary.get("authoritative")),
        "total_judged": _int_or_na(total_judged),
        "semantic_business_correct": _fraction_or_na(correct, total_judged),
        "semantic_business_incorrect": _fraction_or_na(incorrect, total_judged),
        "provider_error": _int_or_na(counts.get("provider_error")),
        "provider_parse_error": _int_or_na(counts.get("provider_parse_error")),
        "redaction_applied": _bool_or_na(redaction.get("redaction_applied")),
    }


def extract_provenance(summary: Mapping[str, Any]) -> dict[str, str]:
    config = summary.get("config") if isinstance(summary.get("config"), Mapping) else {}
    return {
        "dataset_hash": _text_or_na(config.get("dataset_hash")).lower(),
        "selected_cases_hash": _text_or_na(config.get("selected_cases_hash")).lower(),
        "git_commit": _text_or_na(config.get("git_commit")),
        "started_at": _text_or_na(config.get("started_at")),
    }


def evaluate_promotion_rows(
    rows: Sequence[PromotionRow],
    *,
    root: Path,
    include_non_final: bool = False,
    verify: bool = True,
) -> list[ScopeEvaluation]:
    evaluations: list[ScopeEvaluation] = []
    for row in rows:
        errors = row.validation_errors()
        if errors:
            evaluations.append(
                ScopeEvaluation(
                    row=row,
                    included=False,
                    exclusion_reason="; ".join(errors),
                )
            )
            continue
        if not row.is_paper_final:
            evaluations.append(
                ScopeEvaluation(
                    row=row,
                    included=include_non_final,
                    exclusion_reason="" if include_non_final else f"status={row.status}",
                )
            )
            continue
        if not row.artifact_path or row.normalized_artifact_path in {"-", "n/a"}:
            evaluations.append(
                ScopeEvaluation(
                    row=row,
                    included=False,
                    exclusion_reason="paper_final row is missing an artifact path",
                )
            )
            continue
        if row.has_forbidden_final_marker:
            evaluations.append(
                ScopeEvaluation(
                    row=row,
                    included=False,
                    exclusion_reason=(f"forbidden paper_final artifact path: {row.artifact_path}"),
                )
            )
            continue
        verification_ok: bool | None = None
        verification_issues: tuple[str, ...] = ()
        if verify:
            verification_ok, verification_issues = deep_verify_scope(row, root)
            if not verification_ok:
                evaluations.append(
                    ScopeEvaluation(
                        row=row,
                        included=False,
                        exclusion_reason="artifact verification failed",
                        verification_ok=False,
                        verification_issues=verification_issues,
                    )
                )
                continue
        artifact_dir = resolve_artifact_path(row.artifact_path, root)
        summary = load_scope_summary(row, artifact_dir)
        if row.artifact_type == "judge":
            metrics = extract_judge_metrics(summary)
            provenance: dict[str, str] = {}
        else:
            metrics = extract_benchmark_metrics(summary)
            provenance = extract_provenance(summary)
        evaluations.append(
            ScopeEvaluation(
                row=row,
                included=True,
                verification_ok=verification_ok,
                verification_issues=verification_issues,
                metrics=metrics,
                provenance=provenance,
            )
        )
    return evaluations


def _md_cell(value: Any) -> str:
    text = str(value)
    return text.replace("|", "\\|").replace("\r\n", " ").replace("\n", " ").strip()


def _md_row(cells: Sequence[Any]) -> str:
    return "| " + " | ".join(_md_cell(cell) for cell in cells) + " |"


def _md_separator(width: int) -> str:
    return "|---" * width + "|"


def _short_hash(value: str) -> str:
    lowered = value.strip().lower()
    if len(lowered) >= HASH_SHORT_LENGTH and _HEX_RE.fullmatch(lowered):
        return lowered[:HASH_SHORT_LENGTH]
    return lowered if lowered else NA


def _display_path(raw_path: str) -> str:
    return raw_path.replace("\\", "/")


def _benchmark_section(
    evaluations: Sequence[ScopeEvaluation],
    family: str,
    heading: str,
    header: Sequence[str],
    keys: Sequence[str],
) -> list[str]:
    scoped = [
        item
        for item in evaluations
        if item.included
        and item.row.artifact_type == "benchmark"
        and item.evidence_family == family
    ]
    if not scoped:
        return []
    lines = [f"## {heading} ({family})", "", _md_row(header), _md_separator(len(header))]
    for item in scoped:
        cells = [item.scope, _display_path(item.row.artifact_path)]
        cells.extend(item.metrics.get(key, NA) for key in keys)
        lines.append(_md_row(cells))
    lines.append("")
    return lines


def render_paper_tables(
    evaluations: Sequence[ScopeEvaluation],
    *,
    generated_date: str,
    registry_display: str,
    include_diagnostic: bool = False,
) -> str:
    lines: list[str] = [
        "# PARS-SQL Paper Table Pack",
        "",
        f"Generated: {generated_date}",
        "",
        f"Source registry: {registry_display}",
        "",
        "This pack is regenerated from the paper artifact promotion registry and the "
        "verified artifacts behind each promoted scope. It is a reliability-first, "
        "local/private benchmark and framework report for Persian-aware Text-to-SQL.",
        "",
        "Strict execution accuracy, behavioral expected-action accuracy, and "
        "semantic/business correctness under judge are separate metric families and "
        "are never combined in this pack.",
        "",
    ]
    lines.extend(
        _benchmark_section(
            evaluations,
            "sql_positive",
            "Strict SQL-positive benchmark results",
            [
                "Scope",
                "Artifact",
                "Evaluated",
                "Strict EX",
                "Valid SQL rate",
                "Failures",
                "Unsafe SQL",
                "Mean latency ms",
                "P95 latency ms",
            ],
            [
                "total_evaluated",
                "execution_accuracy",
                "valid_sql_rate",
                "failures",
                "unsafe_sql",
                "mean_latency_ms",
                "p95_latency_ms",
            ],
        )
    )
    lines.extend(
        _benchmark_section(
            evaluations,
            "behavioral",
            "Behavioral expected-action benchmark results",
            [
                "Scope",
                "Artifact",
                "Evaluated",
                "Expected-action acc",
                "Safety rejection acc",
                "Clarification acc",
                "Abstention precision",
                "Abstention recall",
            ],
            [
                "total_evaluated",
                "expected_action_accuracy",
                "safety_rejection_accuracy",
                "clarification_accuracy",
                "abstention_precision",
                "abstention_recall",
            ],
        )
    )
    judged = [item for item in evaluations if item.included and item.row.artifact_type == "judge"]
    if judged:
        header = [
            "Provider",
            "Model",
            "Judged",
            "Authoritative",
            "Correct",
            "Incorrect",
            "Provider errors",
            "Parse errors",
            "Redacted",
        ]
        keys = [
            "provider",
            "model",
            "total_judged",
            "authoritative",
            "semantic_business_correct",
            "semantic_business_incorrect",
            "provider_error",
            "provider_parse_error",
            "redaction_applied",
        ]
        lines.append("## Semantic/business judge audit (semantic_business)")
        lines.append("")
        lines.append(_md_row(header))
        lines.append(_md_separator(len(header)))
        for item in judged:
            cells = [item.scope, _display_path(item.row.artifact_path)]
            cells.extend(item.metrics.get(key, NA) for key in keys)
            lines.append(_md_row(cells))
        lines.append("")
    provenance_entries = [item for item in evaluations if item.included and item.provenance]
    if provenance_entries:
        header = [
            "Scope",
            "Artifact type",
            "dataset_hash (sha256-16)",
            "selected_cases_hash (sha256-16)",
            "Git commit",
        ]
        lines.append("## Artifact provenance")
        lines.append("")
        lines.append(_md_row(header))
        lines.append(_md_separator(len(header)))
        for item in provenance_entries:
            lines.append(
                _md_row(
                    [
                        item.scope,
                        item.row.artifact_type,
                        _short_hash(item.provenance.get("dataset_hash", "")),
                        _short_hash(item.provenance.get("selected_cases_hash", "")),
                        item.provenance.get("git_commit", NA),
                    ]
                )
            )
        lines.append("")
    if include_diagnostic:
        diagnostics = [item for item in evaluations if item.is_diagnostic]
        lines.append("## Diagnostic evidence (not paper-final)")
        lines.append("")
        lines.append(
            "Listed for traceability only. These scopes carry no paper metric "
            "promotion and are never cited as final performance."
        )
        lines.append("")
        header = [
            "Scope",
            "Status",
            "Evidence family",
            "Artifact",
            "Paper Metric Allowed",
            "Note",
        ]
        lines.append(_md_row(header))
        lines.append(_md_separator(len(header)))
        for item in diagnostics:
            note = item.exclusion_reason or item.row.notes or "-"
            lines.append(
                _md_row(
                    [
                        item.scope,
                        item.row.status,
                        item.evidence_family,
                        _display_path(item.row.artifact_path),
                        item.row.paper_metric_allowed_raw or NA,
                        note,
                    ]
                )
            )
        lines.append("")
    lines.append("## Reporting constraints")
    lines.append("")
    for constraint in REPORTING_CONSTRAINTS:
        lines.append(f"- {constraint}")
    lines.append("")
    return "\n".join(lines)


def build_manifest_payload(
    evaluations: Sequence[ScopeEvaluation],
    *,
    generated_date: str,
    registry_display: str,
    registry_sha256: str,
    include_diagnostic: bool,
) -> dict[str, Any]:
    scopes: dict[str, Any] = {}
    for item in evaluations:
        scopes[item.scope] = {
            "status": item.row.status,
            "artifact_type": item.row.artifact_type,
            "evidence_family": item.row.evidence_family,
            "artifact_dir": _display_path(item.row.artifact_path),
            "paper_metric_allowed": item.row.paper_metric_allowed_raw,
            "included": item.included,
            "diagnostic": item.is_diagnostic,
            "verification_ok": item.verification_ok,
            "verification_issues": list(item.verification_issues),
            "metrics": dict(item.metrics),
            "provenance": dict(item.provenance),
            "notes": item.row.notes,
        }
    return {
        "schema_version": 1,
        "status": "artifact_backed_paper_pack",
        "generated": generated_date,
        "source_registry": registry_display,
        "source_registry_sha256": registry_sha256,
        "include_diagnostic": include_diagnostic,
        "included_scopes": [item.scope for item in evaluations if item.included],
        "excluded_scopes": [
            {"scope": item.scope, "reason": item.exclusion_reason}
            for item in evaluations
            if not item.included
        ],
        "scopes": scopes,
        "reporting_constraints": list(REPORTING_CONSTRAINTS),
    }
