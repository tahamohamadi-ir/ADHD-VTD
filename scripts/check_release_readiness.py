from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Imports below need PROJECT_ROOT on sys.path when this file runs as a script.
from scripts.verify_artifact import verify_artifact  # noqa: E402
from src.evaluation.candidate_adoption_review import (  # noqa: E402
    validate_candidate_adoption_review_package,
)
from src.evaluation.judge_ablation_plan import (  # noqa: E402
    validate_dual_policy_judge_ablation_plan,
)
from src.evaluation.llm_judge import validate_judge_artifact  # noqa: E402
from src.evaluation.multi_candidate_ablation import (  # noqa: E402
    validate_multi_candidate_ablation_artifact,
)

STALE_REFERENCE_PATTERNS = {
    "BENCHMARK_PROTOCOL.md": "Use docs/context-hub/ARTIFACT_RULES.md as the canonical benchmark/artifact protocol.",
    "docs/context-hub/query-shape-contracts.md": "Use docs/context-hub/QUERY_SHAPE_CONTRACTS.md.",
    "docs/context-hub/failure-patterns.md": "Use docs/context-hub/FAILURE_PATTERNS.md.",
    "DATASET_CARD_DRAFT.md": "Use docs/DATASET_CARD.md.",
    "README_PHASE0_SNIPPET.md": "Phase 0 notes are folded into docs/DATASET_CARD.md.",
    "CHANGELOG_UPDATED_DOCS.md": "Do not depend on the old docs package changelog.",
    "reproduce_paper_results.py": "Use scripts/check_release_readiness.py and docs/PARS_SQL_PAPER1_REPRODUCIBILITY.md.",
    "reproduce_paper.ps1": "Use the current Python verification scripts unless this script is added back.",
    "make_paper_tables.py": "Use artifact-backed packaging scripts unless this generator is added back.",
    "verify_dataset_hashes.py": "Use scripts/verify_artifact.py and scripts/check_release_readiness.py for current dataset hash drift checks.",
    "src/generation/context_builder.py": "Use src/retrieval/context_builder.py.",
}

FORBIDDEN_PAPER_CLAIMS = {
    "state-of-the-art",
    "high accuracy",
    "clinical decision support",
    "diagnostic system",
    "guarantees privacy",
    "solves Persian Text-to-SQL",
    "schema linking significantly improves EX",
    "value linking significantly improves EX",
}

METRIC_FAMILY_TERMS = {
    "sql_positive": (
        "strict ex",
        "strict execution",
        "execution accuracy",
        "conservative execution",
        "valid sql rate",
        "invalid sql",
        "missing sql",
        "result mismatch",
        "sql-positive",
        "sql positive",
        "unsafe sql",
        "latency mean",
        "latency p95",
    ),
    "semantic_business": (
        "semantic/business",
        "semantic business",
        "semantic correctness",
        "business correctness",
        "semantic judge",
        "llm judge",
        "llm-as-a-judge",
        "judge correctness",
        "human review correctness",
        "dual-policy",
        "judge policy",
    ),
    "behavioral": (
        "behavioral",
        "expected-action",
        "expected action accuracy",
        "safety rejection accuracy",
        "clarification accuracy",
        "abstention precision",
        "abstention recall",
    ),
}

METRIC_SEPARATION_LANGUAGE = (
    "separate",
    "separated",
    "separately",
    "distinct",
    "not combined",
    "not combine",
    "never combine",
    "do not combine",
    "not mixed",
    "not mix",
    "never mix",
    "do not mix",
    "reported separately",
    "different denominator",
    "different denominators",
)

PAPER_TABLE_PROVENANCE_TERMS = ("dataset_hash", "selected_cases_hash")
PAPER_TABLE_ARTIFACT_TERMS = (
    "artifact provenance",
    "summary_json",
    "predictions",
    "benchmark_results_csv",
    "manifest",
)

PROMOTION_REQUIRED_COLUMNS = {
    "scope",
    "artifact_type",
    "artifact_path",
    "evidence_family",
    "status",
    "paper_metric_allowed",
}
PROMOTION_ALLOWED_STATUSES = {"paper_final", "diagnostic_only", "pending_review"}
PROMOTION_ALLOWED_FAMILIES = {"sql_positive", "semantic_business", "behavioral"}
PROMOTION_ALLOWED_TYPES = {"benchmark", "judge"}
PROMOTION_FINAL_FORBIDDEN_SUBSTRINGS = (
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

STANDARD_PAPER_DOC_PATHS = (
    PROJECT_ROOT / "docs" / "00_INDEX.md",
    PROJECT_ROOT / "docs" / "01_RESEARCH_GRADE_ARCHITECTURE.md",
    PROJECT_ROOT / "docs" / "02_LANGGRAPH_WORKFLOW_SPEC.md",
    PROJECT_ROOT / "docs" / "03_PERSIAN_NLU_AND_SCHEMA_LINKING.md",
    PROJECT_ROOT / "docs" / "04_RAG_CAG_AND_RETRIEVAL_DESIGN.md",
    PROJECT_ROOT / "docs" / "05_SQL_GENERATION_VALIDATION_REFLEXION.md",
    PROJECT_ROOT / "docs" / "06_EVALUATION_ABLATION_AND_PAPER_PLAN.md",
    PROJECT_ROOT / "docs" / "07_IMPLEMENTATION_ROADMAP_AND_REQUIREMENTS.md",
    PROJECT_ROOT / "docs" / "08_PROJECT_STRUCTURE_AND_FILE_MAP.md",
    PROJECT_ROOT / "docs" / "09_DATASET_AND_EVALUATION_FILES_GUIDE.md",
    PROJECT_ROOT / "docs" / "10_FULL_DEVELOPMENT_ROADMAP_ZERO_TO_SOTA.md",
    PROJECT_ROOT / "docs" / "11_SEMANTIC_BUSINESS_LOGIC_EVALUATION.md",
    PROJECT_ROOT / "docs" / "DATASET_CARD.md",
    PROJECT_ROOT / "docs" / "BENCHMARK_AND_TEST_GUIDE.md",
    PROJECT_ROOT / "docs" / "PARS_SQL_PAPER1_IMPLEMENTATION_PLAN.md",
    PROJECT_ROOT / "docs" / "PARS_SQL_PAPER1_RESULTS_SUMMARY.md",
    PROJECT_ROOT / "docs" / "PARS_SQL_PAPER1_REPRODUCIBILITY.md",
    PROJECT_ROOT / "docs" / "PHASE0_50Q_AUDIT_TEMPLATE.md",
    PROJECT_ROOT / "docs" / "README.md",
    PROJECT_ROOT / "docs" / "Risks.md",
    PROJECT_ROOT / "docs" / "THREAT_MODEL.md",
    PROJECT_ROOT / "docs" / "paper" / "limitations.md",
    PROJECT_ROOT
    / "results"
    / "paper"
    / "20260520_phase16_a4_dual_policy_evidence"
    / "paper_evidence_table.md",
    PROJECT_ROOT / "CODEX_PROMPTS.md",
)
STANDARD_PAPER_DOC_GLOBS = (
    PROJECT_ROOT / "docs" / "context-hub" / "*.md",
    PROJECT_ROOT / ".codex" / "prompts" / "*.md",
    PROJECT_ROOT / ".aiassistant" / "rules" / "*.md",
)
PROMOTION_FINAL_FORBIDDEN_SPL_RE = re.compile(r"(^|[/_-])spl\d+($|[/_-])")
PROMOTION_TRUE_VALUES = {"true", "yes", "1"}
PROMOTION_FALSE_VALUES = {"false", "no", "0"}

SQL_EXECUTION_ALLOWED_PATHS = {
    Path("src/db/read_only_executor.py"),
    Path("src/db/sqlite_connection.py"),
    Path("src/db/schema_inspector.py"),
}
RISK_ALLOWED_BLOCKER_CATEGORIES = frozenset(
    {
        "actionable_nonhuman",
        "blocked_human_review",
        "blocked_external_api",
        "paper_promotion_pending",
    }
)
RISK_REQUIRED_OPEN_FIELDS = (
    "Current guard",
    "Next action",
    "Close condition",
)
RISK_HEADING_RE = re.compile(r"(?m)^##\s+(R\d+)\.\s+(.+?)\s*$")


@dataclass(frozen=True)
class ReleaseIssue:
    code: str
    message: str
    path: str | None = None
    severity: str = "error"

    def as_dict(self) -> dict[str, str]:
        payload = {
            "code": self.code,
            "message": self.message,
            "severity": self.severity,
        }
        if self.path is not None:
            payload["path"] = self.path
        return payload


@dataclass(frozen=True)
class ReleaseReadinessReport:
    ok: bool
    issues: list[ReleaseIssue] = field(default_factory=list)
    checked: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "issues": [issue.as_dict() for issue in self.issues],
            "checked": self.checked,
        }


def parse_dual_policy_pair(value: str) -> tuple[Path, Path]:
    if "=" not in value:
        raise argparse.ArgumentTypeError(
            "--dual-policy-pair must use benchmark_artifact_dir=dual_policy_dir"
        )
    benchmark, dual_policy = value.split("=", 1)
    if not benchmark.strip() or not dual_policy.strip():
        raise argparse.ArgumentTypeError(
            "--dual-policy-pair must include both benchmark and dual-policy paths"
        )
    return Path(benchmark), Path(dual_policy)


def _dedupe_paths(paths: Iterable[str | Path]) -> list[Path]:
    seen: set[str] = set()
    unique: list[Path] = []
    for raw_path in paths:
        path = Path(raw_path)
        key = str(path).lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(path)
    return unique


def standard_paper_docs() -> list[Path]:
    docs: list[Path] = list(STANDARD_PAPER_DOC_PATHS)
    for glob_pattern in STANDARD_PAPER_DOC_GLOBS:
        parent = glob_pattern.parent
        if parent.exists():
            docs.extend(sorted(parent.glob(glob_pattern.name)))
    return _dedupe_paths(docs)


def check_release_readiness(
    *,
    benchmark_artifact_dirs: Sequence[str | Path] = (),
    dual_policy_pairs: Sequence[tuple[str | Path, str | Path]] = (),
    comparison_artifact_dirs: Sequence[str | Path] = (),
    candidate_review_dirs: Sequence[str | Path] = (),
    judge_ablation_plan_dirs: Sequence[str | Path] = (),
    judge_artifact_dirs: Sequence[str | Path] = (),
    paper_docs: Sequence[str | Path] = (),
    promotion_docs: Sequence[str | Path] = (),
    sql_execution_paths: Sequence[str | Path] | None = None,
    reference_paths: Sequence[str | Path] | None = None,
    required_paths: Sequence[str | Path] | None = None,
    risks_path: str | Path | None = PROJECT_ROOT / "docs" / "Risks.md",
    fail_on_open_risks: bool = False,
    fail_on_actionable_risks: bool = False,
    include_standard_paper_docs: bool = False,
) -> ReleaseReadinessReport:
    effective_paper_docs = _dedupe_paths(
        [
            *paper_docs,
            *(standard_paper_docs() if include_standard_paper_docs else ()),
        ]
    )
    issues: list[ReleaseIssue] = []
    checked: dict[str, Any] = {
        "benchmark_artifacts": [],
        "dual_policy_pairs": [],
        "comparison_artifacts": [],
        "candidate_review_packages": [],
        "judge_ablation_plans": [],
        "judge_artifacts": [],
        "paper_docs": [str(path) for path in effective_paper_docs],
        "standard_paper_docs_included": include_standard_paper_docs,
        "promotion_docs": [str(Path(path)) for path in promotion_docs],
    }

    for artifact_dir in benchmark_artifact_dirs:
        artifact_path = Path(artifact_dir)
        report = verify_artifact(artifact_path)
        checked["benchmark_artifacts"].append(report.as_dict())
        _extend_artifact_issues(issues, report.issues, artifact_path)

    for benchmark_dir, dual_policy_dir in dual_policy_pairs:
        benchmark_path = Path(benchmark_dir)
        dual_policy_path = Path(dual_policy_dir)
        report = verify_artifact(benchmark_path, dual_policy_dir=dual_policy_path)
        pair_payload = report.as_dict()
        pair_payload["dual_policy_dir"] = str(dual_policy_path)
        checked["dual_policy_pairs"].append(pair_payload)
        _extend_artifact_issues(issues, report.issues, benchmark_path, dual_policy_path)

    for comparison_dir in comparison_artifact_dirs:
        comparison_path = Path(comparison_dir)
        report = validate_multi_candidate_ablation_artifact(comparison_path)
        checked["comparison_artifacts"].append(report.as_dict())
        for issue in report.issues:
            code = str(issue.code)
            if not code.startswith("COMPARISON_"):
                code = f"COMPARISON_{code}"
            issues.append(
                ReleaseIssue(
                    code=code,
                    message=issue.message,
                    path=issue.path,
                    severity=issue.severity,
                )
            )

    for review_dir in candidate_review_dirs:
        review_path = Path(review_dir)
        report = validate_candidate_adoption_review_package(review_path)
        checked["candidate_review_packages"].append(report.as_dict())
        for issue in report.issues:
            code = str(issue.code)
            if not code.startswith("CANDIDATE_REVIEW_"):
                code = f"CANDIDATE_REVIEW_{code}"
            issues.append(
                ReleaseIssue(
                    code=code,
                    message=issue.message,
                    path=issue.path,
                    severity=issue.severity,
                )
            )

    for plan_dir in judge_ablation_plan_dirs:
        plan_path = Path(plan_dir)
        report = validate_dual_policy_judge_ablation_plan(plan_path)
        plan_payload = report.as_dict()
        checked["judge_ablation_plans"].append(plan_payload)
        for issue in report.issues:
            code = str(issue.code)
            if not code.startswith("JUDGE_ABLATION_PLAN_"):
                if code.startswith("PLAN_"):
                    code = code.removeprefix("PLAN_")
                code = f"JUDGE_ABLATION_PLAN_{code}"
            issues.append(
                ReleaseIssue(
                    code=code,
                    message=issue.message,
                    path=issue.path,
                    severity=issue.severity,
                )
            )
        if report.ok:
            for role in ("baseline_artifact_dir", "adaptive_artifact_dir"):
                artifact_path = Path(str(report.checked.get(role) or ""))
                artifact_report = verify_artifact(artifact_path)
                plan_payload.setdefault("input_artifacts", {})[role] = artifact_report.as_dict()
                _extend_artifact_issues(
                    issues,
                    artifact_report.issues,
                    artifact_path,
                    code_prefix=f"JUDGE_ABLATION_PLAN_{role.upper()}_",
                )

    for judge_dir in judge_artifact_dirs:
        judge_path = Path(judge_dir)
        report = validate_judge_artifact(judge_path, require_authoritative=True)
        checked["judge_artifacts"].append(report.as_dict())
        for issue in report.issues:
            code = str(issue.code)
            if not code.startswith("JUDGE_ARTIFACT_") and not code.startswith("JUDGE_"):
                code = f"JUDGE_ARTIFACT_{code}"
            issues.append(
                ReleaseIssue(
                    code=code,
                    message=issue.message,
                    path=issue.path,
                    severity=issue.severity,
                )
            )

    for path in required_paths if required_paths is not None else _default_required_paths():
        required = Path(path)
        if not required.exists():
            issues.append(
                ReleaseIssue(
                    code="REQUIRED_RELEASE_PATH_MISSING",
                    message=f"Required release path is missing: {required}",
                    path=str(required),
                )
            )

    stale_paths = (
        list(reference_paths) if reference_paths is not None else _default_reference_paths()
    )
    stale_count = _check_stale_references(issues, stale_paths)
    checked["stale_reference_files_checked"] = len(stale_paths)
    checked["stale_reference_issues"] = stale_count

    claim_count = _check_paper_claims(issues, effective_paper_docs)
    checked["paper_claim_issues"] = claim_count
    family_count = _check_paper_metric_family_separation(issues, effective_paper_docs)
    checked["paper_metric_family_issues"] = family_count
    provenance_count = _check_paper_table_provenance(issues, effective_paper_docs)
    checked["paper_table_provenance_issues"] = provenance_count
    promotion_count, promotion_rows = _check_promotion_docs(issues, promotion_docs)
    checked["promotion_registry_rows"] = promotion_rows
    checked["promotion_registry_issues"] = promotion_count

    sql_execution_count, sql_execution_files_checked = _check_sql_execution_paths(
        issues,
        sql_execution_paths,
    )
    checked["sql_execution_files_checked"] = sql_execution_files_checked
    checked["sql_execution_path_issues"] = sql_execution_count

    risk_report = _validate_open_risks(issues, risks_path)
    open_risks = int(risk_report["open_count"])
    actionable_open_risks = int(risk_report["categories"]["actionable_nonhuman"])
    checked["open_risks"] = open_risks
    checked["open_risk_categories"] = risk_report["categories"]
    checked["risk_schema_issues"] = risk_report["schema_issues"]
    checked["actionable_open_risks"] = actionable_open_risks
    if fail_on_open_risks and open_risks > 0:
        issues.append(
            ReleaseIssue(
                code="OPEN_RISKS_PRESENT",
                message=f"docs/Risks.md still contains {open_risks} open risk entries.",
                path=str(risks_path) if risks_path else None,
            )
        )
    if fail_on_actionable_risks and actionable_open_risks > 0:
        issues.append(
            ReleaseIssue(
                code="ACTIONABLE_OPEN_RISKS_PRESENT",
                message=(
                    "docs/Risks.md still contains "
                    f"{actionable_open_risks} actionable non-human open risk entries."
                ),
                path=str(risks_path) if risks_path else None,
            )
        )

    return ReleaseReadinessReport(ok=not issues, issues=issues, checked=checked)


def _extend_artifact_issues(
    issues: list[ReleaseIssue],
    artifact_issues: Sequence[Any],
    artifact_path: Path,
    dual_policy_path: Path | None = None,
    code_prefix: str | None = None,
) -> None:
    for issue in artifact_issues:
        prefix = (
            code_prefix
            if code_prefix is not None
            else "DUAL_POLICY_"
            if dual_policy_path
            else "ARTIFACT_"
        )
        code = str(issue.code)
        if not code.startswith(prefix):
            code = f"{prefix}{code}"
        path = f"{artifact_path} :: {dual_policy_path}" if dual_policy_path else str(artifact_path)
        issues.append(
            ReleaseIssue(
                code=code,
                message=issue.message,
                path=path,
            )
        )


def _default_required_paths() -> list[Path]:
    return [
        PROJECT_ROOT / "AGENTS.md",
        PROJECT_ROOT / "docs" / "context-hub" / "INDEX.md",
        PROJECT_ROOT / "docs" / "context-hub" / "ARTIFACT_RULES.md",
        PROJECT_ROOT / "docs" / "context-hub" / "SAFETY_PRIVACY_RULES.md",
        PROJECT_ROOT / "docs" / "Risks.md",
        PROJECT_ROOT / "scripts" / "verify_artifact.py",
        PROJECT_ROOT / "scripts" / "package_dual_policy_evidence.py",
    ]


def _default_reference_paths() -> list[Path]:
    candidates: list[Path] = []
    roots = [
        PROJECT_ROOT / "docs",
        PROJECT_ROOT / "docs" / "context-hub",
        PROJECT_ROOT / ".codex" / "prompts",
        PROJECT_ROOT / ".aiassistant" / "rules",
    ]
    for root in roots:
        if root.exists():
            candidates.extend(sorted(root.glob("*.md")))
    skills_root = PROJECT_ROOT / ".agents" / "skills"
    if skills_root.exists():
        candidates.extend(sorted(skills_root.glob("*/SKILL.md")))
    candidates.extend(
        path
        for path in [
            PROJECT_ROOT / "scripts" / "README.md",
            PROJECT_ROOT / "CODEX_PROMPTS.md",
        ]
        if path.exists()
    )
    return _unique_paths(candidates)


def _unique_paths(paths: Iterable[Path]) -> list[Path]:
    seen: set[Path] = set()
    unique: list[Path] = []
    for path in paths:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        unique.append(path)
    return unique


def _check_stale_references(issues: list[ReleaseIssue], paths: Sequence[str | Path]) -> int:
    count = 0
    for raw_path in paths:
        path = Path(raw_path)
        if not path.exists() or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for pattern, replacement in STALE_REFERENCE_PATTERNS.items():
            if pattern in text:
                count += 1
                issues.append(
                    ReleaseIssue(
                        code="STALE_REFERENCE",
                        message=f"Found stale reference {pattern!r}. {replacement}",
                        path=str(path),
                    )
                )
    return count


def _check_paper_claims(issues: list[ReleaseIssue], paper_docs: Sequence[str | Path]) -> int:
    count = 0
    for raw_path in paper_docs:
        path = Path(raw_path)
        if not path.exists() or not path.is_file():
            issues.append(
                ReleaseIssue(
                    code="PAPER_DOC_MISSING",
                    message=f"Paper claim document not found: {path}",
                    path=str(path),
                )
            )
            count += 1
            continue
        text = path.read_text(encoding="utf-8").lower()
        for phrase in FORBIDDEN_PAPER_CLAIMS:
            if phrase.lower() in text:
                count += 1
                issues.append(
                    ReleaseIssue(
                        code="FORBIDDEN_PAPER_CLAIM",
                        message=f"Forbidden or unproven paper claim phrase found: {phrase!r}.",
                        path=str(path),
                    )
                )
    return count


def _check_paper_metric_family_separation(
    issues: list[ReleaseIssue],
    paper_docs: Sequence[str | Path],
) -> int:
    count = 0
    for raw_path in paper_docs:
        path = Path(raw_path)
        if not path.exists() or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for segment in _paper_claim_segments(text):
            normalized = " ".join(segment.lower().split())
            families = [
                family
                for family, terms in METRIC_FAMILY_TERMS.items()
                if any(term in normalized for term in terms)
            ]
            if len(families) < 2 or _has_metric_separation_language(normalized):
                continue
            count += 1
            snippet = segment.strip().replace("\n", " ")
            if len(snippet) > 180:
                snippet = f"{snippet[:177]}..."
            issues.append(
                ReleaseIssue(
                    code="MIXED_METRIC_FAMILIES",
                    message=(
                        "Paper-facing text appears to mix metric families without "
                        f"explicit separation: {', '.join(families)}. Segment: {snippet!r}."
                    ),
                    path=str(path),
                )
            )
    return count


def _paper_claim_segments(text: str) -> list[str]:
    segments: list[str] = []
    paragraph: list[str] = []
    in_fence = False

    def flush_paragraph() -> None:
        if paragraph:
            segments.append(" ".join(paragraph))
            paragraph.clear()

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith("```"):
            flush_paragraph()
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if not line:
            flush_paragraph()
            continue
        lower = line.lower()
        is_table_row = line.startswith("|") and line.endswith("|")
        is_caption = lower.startswith(("table ", "figure ", "caption:"))
        if is_table_row or is_caption:
            flush_paragraph()
            segments.append(line)
            continue
        paragraph.append(line)

    flush_paragraph()
    return segments


def _has_metric_separation_language(segment: str) -> bool:
    return any(marker in segment for marker in METRIC_SEPARATION_LANGUAGE)


def _check_paper_table_provenance(
    issues: list[ReleaseIssue],
    paper_docs: Sequence[str | Path],
) -> int:
    count = 0
    for raw_path in paper_docs:
        path = Path(raw_path)
        if not path.exists() or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        normalized = text.lower()
        if not _looks_like_paper_table(path, normalized):
            continue
        missing_hash_terms = [
            term for term in PAPER_TABLE_PROVENANCE_TERMS if term not in normalized
        ]
        has_artifact_provenance = any(term in normalized for term in PAPER_TABLE_ARTIFACT_TERMS)
        if not missing_hash_terms and has_artifact_provenance:
            continue
        count += 1
        details: list[str] = []
        if missing_hash_terms:
            details.append(f"missing {', '.join(missing_hash_terms)}")
        if not has_artifact_provenance:
            details.append("missing artifact provenance")
        issues.append(
            ReleaseIssue(
                code="PAPER_TABLE_PROVENANCE_MISSING",
                message=(
                    "Paper table markdown must include dataset/split hashes and "
                    f"artifact provenance ({'; '.join(details)})."
                ),
                path=str(path),
            )
        )
    return count


def _looks_like_paper_table(path: Path, normalized_text: str) -> bool:
    name = path.name.lower()
    return (
        "paper_tables" in name
        or "paper tables" in normalized_text
        or "## table 1" in normalized_text
    )


def _check_promotion_docs(
    issues: list[ReleaseIssue],
    promotion_docs: Sequence[str | Path],
) -> tuple[int, int]:
    count = 0
    rows_checked = 0
    for raw_path in promotion_docs:
        path = Path(raw_path)
        if not path.exists() or not path.is_file():
            count += 1
            issues.append(
                ReleaseIssue(
                    code="PROMOTION_DOC_MISSING",
                    message=f"Promotion registry document not found: {path}",
                    path=str(path),
                )
            )
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            count += 1
            issues.append(
                ReleaseIssue(
                    code="PROMOTION_DOC_UNREADABLE",
                    message=f"Promotion registry document is not valid UTF-8: {path}",
                    path=str(path),
                )
            )
            continue
        registry_rows = _promotion_registry_rows(text)
        if not registry_rows:
            count += 1
            issues.append(
                ReleaseIssue(
                    code="PROMOTION_REGISTRY_MISSING",
                    message=(
                        "Promotion document must contain a markdown table with "
                        f"columns: {', '.join(sorted(PROMOTION_REQUIRED_COLUMNS))}."
                    ),
                    path=str(path),
                )
            )
            continue
        for row in registry_rows:
            rows_checked += 1
            count += _check_promotion_row(issues, path, row)
    return count, rows_checked


def _promotion_registry_rows(text: str) -> list[dict[str, str]]:
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
        row_index = index + 2
        while row_index < len(lines) and _looks_like_markdown_table_row(lines[row_index]):
            cells = [_normalize_table_cell(cell) for cell in _split_markdown_row(lines[row_index])]
            if cells:
                rows.append(
                    {
                        required: (
                            cells[column_indexes[required]]
                            if column_indexes[required] < len(cells)
                            else ""
                        )
                        for required in PROMOTION_REQUIRED_COLUMNS
                    }
                )
            row_index += 1
    return rows


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


def _check_promotion_row(
    issues: list[ReleaseIssue],
    doc_path: Path,
    row: dict[str, str],
) -> int:
    count = 0
    status = row["status"].strip().lower()
    artifact_type = row["artifact_type"].strip().lower()
    evidence_family = row["evidence_family"].strip().lower()
    raw_artifact_path = row["artifact_path"].strip()
    paper_metric_allowed = _parse_promotion_bool(row["paper_metric_allowed"])

    if status not in PROMOTION_ALLOWED_STATUSES:
        count += 1
        issues.append(
            ReleaseIssue(
                code="PROMOTION_STATUS_INVALID",
                message=f"Invalid promotion status {status!r}.",
                path=str(doc_path),
            )
        )
    if artifact_type not in PROMOTION_ALLOWED_TYPES:
        count += 1
        issues.append(
            ReleaseIssue(
                code="PROMOTION_ARTIFACT_TYPE_INVALID",
                message=f"Invalid promotion artifact type {artifact_type!r}.",
                path=str(doc_path),
            )
        )
    if evidence_family not in PROMOTION_ALLOWED_FAMILIES:
        count += 1
        issues.append(
            ReleaseIssue(
                code="PROMOTION_EVIDENCE_FAMILY_INVALID",
                message=f"Invalid evidence family {evidence_family!r}.",
                path=str(doc_path),
            )
        )
    if paper_metric_allowed is None:
        count += 1
        issues.append(
            ReleaseIssue(
                code="PROMOTION_METRIC_ALLOWED_INVALID",
                message=(
                    "paper_metric_allowed must be true/false, yes/no, or 1/0 "
                    f"for scope {row['scope']!r}."
                ),
                path=str(doc_path),
            )
        )
    elif status in {"diagnostic_only", "pending_review"} and paper_metric_allowed:
        count += 1
        issues.append(
            ReleaseIssue(
                code="PROMOTION_NONFINAL_METRIC_ALLOWED",
                message=(
                    f"Non-final promotion status {status!r} cannot allow paper metrics "
                    f"for scope {row['scope']!r}."
                ),
                path=str(doc_path),
            )
        )

    if artifact_type == "judge" and evidence_family != "semantic_business":
        count += 1
        issues.append(
            ReleaseIssue(
                code="PROMOTION_TYPE_FAMILY_MISMATCH",
                message="Judge artifacts must be registered as semantic_business evidence.",
                path=str(doc_path),
            )
        )
    elif artifact_type == "benchmark" and evidence_family == "semantic_business":
        count += 1
        issues.append(
            ReleaseIssue(
                code="PROMOTION_TYPE_FAMILY_MISMATCH",
                message=(
                    "Semantic/business evidence must come from judge or dual-policy "
                    "artifacts, not raw benchmark artifacts."
                ),
                path=str(doc_path),
            )
        )

    if status != "paper_final":
        return count

    if not raw_artifact_path or raw_artifact_path in {"-", "n/a", "N/A"}:
        count += 1
        issues.append(
            ReleaseIssue(
                code="PROMOTION_FINAL_ARTIFACT_PATH_MISSING",
                message=f"paper_final scope {row['scope']!r} must include an artifact path.",
                path=str(doc_path),
            )
        )
        return count

    normalized_path = raw_artifact_path.replace("\\", "/").lower()
    if _has_forbidden_final_marker(normalized_path):
        count += 1
        issues.append(
            ReleaseIssue(
                code="PROMOTION_FORBIDDEN_FINAL_ARTIFACT",
                message=(
                    "paper_final rows cannot point at smoke, dry-run, mock, pending, "
                    f"shadow, SPL, failed, or diagnostic artifacts: {raw_artifact_path}"
                ),
                path=str(doc_path),
            )
        )

    artifact_path = _resolve_promotion_path(raw_artifact_path)
    if artifact_type == "benchmark":
        report = verify_artifact(artifact_path)
        _extend_artifact_issues(
            issues,
            report.issues,
            artifact_path,
            code_prefix="PROMOTION_BENCHMARK_",
        )
        count += len(report.issues)
    elif artifact_type == "judge":
        report = validate_judge_artifact(artifact_path, require_authoritative=True)
        for issue in report.issues:
            count += 1
            code = str(issue.code)
            if not code.startswith("PROMOTION_JUDGE_"):
                code = f"PROMOTION_JUDGE_{code}"
            issues.append(
                ReleaseIssue(
                    code=code,
                    message=issue.message,
                    path=issue.path or str(artifact_path),
                    severity=issue.severity,
                )
            )
    return count


def _has_forbidden_final_marker(normalized_path: str) -> bool:
    return any(
        marker in normalized_path for marker in PROMOTION_FINAL_FORBIDDEN_SUBSTRINGS
    ) or bool(PROMOTION_FINAL_FORBIDDEN_SPL_RE.search(normalized_path))


def _parse_promotion_bool(value: str) -> bool | None:
    normalized = value.strip().lower()
    if normalized in PROMOTION_TRUE_VALUES:
        return True
    if normalized in PROMOTION_FALSE_VALUES:
        return False
    return None


def _resolve_promotion_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def _check_sql_execution_paths(
    issues: list[ReleaseIssue],
    paths: Sequence[str | Path] | None,
) -> tuple[int, int]:
    candidates = (
        [Path(path) for path in paths] if paths is not None else _default_sql_execution_scan_paths()
    )
    count = 0
    checked = 0
    for path in candidates:
        if not path.exists() or not path.is_file() or path.suffix != ".py":
            continue
        checked += 1
        if _is_allowed_sql_execution_path(path):
            continue
        try:
            text = path.read_text(encoding="utf-8")
            issue_codes = _sql_execution_issue_codes(text)
        except (SyntaxError, UnicodeDecodeError):
            continue
        for code in issue_codes:
            count += 1
            issues.append(
                ReleaseIssue(
                    code=code,
                    message=(
                        "Direct SQL execution is only allowed through the read-only "
                        "DB execution paths."
                    ),
                    path=str(path),
                )
            )
    return count, checked


def _sql_execution_issue_codes(text: str) -> list[str]:
    tree = ast.parse(text)
    codes: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not isinstance(func, ast.Attribute):
            continue
        if (
            func.attr == "connect"
            and isinstance(func.value, ast.Name)
            and func.value.id == "sqlite3"
        ):
            codes.append("DIRECT_SQLITE_CONNECTION")
        elif func.attr == "execute":
            codes.append("DIRECT_SQL_EXECUTE")
        elif func.attr == "executescript":
            codes.append("SQL_EXECUTESCRIPT")
    return sorted(set(codes))


def _default_sql_execution_scan_paths() -> list[Path]:
    candidates: list[Path] = []
    for root in (PROJECT_ROOT / "src", PROJECT_ROOT / "scripts"):
        if root.exists():
            candidates.extend(sorted(root.rglob("*.py")))
    return candidates


def _is_allowed_sql_execution_path(path: Path) -> bool:
    try:
        relative = path.resolve().relative_to(PROJECT_ROOT.resolve())
    except ValueError:
        return False
    return relative in SQL_EXECUTION_ALLOWED_PATHS


def _validate_open_risks(
    issues: list[ReleaseIssue],
    risks_path: str | Path | None,
) -> dict[str, Any]:
    categories = {category: 0 for category in sorted(RISK_ALLOWED_BLOCKER_CATEGORIES)}
    report: dict[str, Any] = {
        "open_count": 0,
        "categories": categories,
        "schema_issues": 0,
    }
    if risks_path is None:
        return report
    path = Path(risks_path)
    if not path.exists():
        return report
    issue_count_before = len(issues)
    text = path.read_text(encoding="utf-8")
    for risk_id, title, section in _iter_risk_sections(text):
        status = _risk_field(section, "Status")
        if (status or "").strip().lower() != "open":
            continue
        report["open_count"] += 1
        label = f"{risk_id}. {title}"
        category = _risk_field(section, "Blocker category")
        if _is_missing_risk_field(category):
            issues.append(
                ReleaseIssue(
                    code="RISK_BLOCKER_CATEGORY_MISSING",
                    message=f"Open risk {label} is missing a blocker category.",
                    path=str(path),
                )
            )
        elif category not in RISK_ALLOWED_BLOCKER_CATEGORIES:
            issues.append(
                ReleaseIssue(
                    code="RISK_BLOCKER_CATEGORY_INVALID",
                    message=(
                        f"Open risk {label} has invalid blocker category {category!r}. "
                        "Use one of: "
                        f"{', '.join(sorted(RISK_ALLOWED_BLOCKER_CATEGORIES))}."
                    ),
                    path=str(path),
                )
            )
        else:
            categories[category] += 1

        for field_name in RISK_REQUIRED_OPEN_FIELDS:
            if _is_missing_risk_field(_risk_field(section, field_name)):
                issues.append(
                    ReleaseIssue(
                        code="RISK_FIELD_MISSING",
                        message=f"Open risk {label} is missing required field: {field_name}.",
                        path=str(path),
                    )
                )
        if category == "actionable_nonhuman" and _is_missing_risk_field(
            _risk_field(section, "Guard command")
        ):
            issues.append(
                ReleaseIssue(
                    code="RISK_GUARD_COMMAND_MISSING",
                    message=(
                        f"Open risk {label} is actionable without human review but "
                        "does not name a concrete guard command."
                    ),
                    path=str(path),
                )
            )

    report["schema_issues"] = len(issues) - issue_count_before
    return report


def _iter_risk_sections(text: str) -> Iterable[tuple[str, str, str]]:
    headings = list(RISK_HEADING_RE.finditer(text))
    for index, heading in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        yield heading.group(1), heading.group(2).strip(), text[heading.start() : end]


def _risk_field(section: str, field_name: str) -> str | None:
    pattern = re.compile(rf"(?im)^\s*-\s*{re.escape(field_name)}:\s*(.*)$")
    match = pattern.search(section)
    if match is None:
        return None
    return match.group(1).strip()


def _is_missing_risk_field(value: str | None) -> bool:
    if value is None:
        return True
    normalized = value.strip()
    return not normalized or normalized.startswith("<") or normalized.lower() in {"todo", "tbd"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run paper/release readiness checks without modifying artifacts."
    )
    parser.add_argument(
        "--benchmark-artifact-dir",
        action="append",
        default=[],
        help="Benchmark artifact directory to verify. Repeatable.",
    )
    parser.add_argument(
        "--dual-policy-pair",
        action="append",
        default=[],
        type=parse_dual_policy_pair,
        help="Verify benchmark/dual-policy evidence as benchmark_dir=dual_policy_dir. Repeatable.",
    )
    parser.add_argument(
        "--candidate-review-dir",
        action="append",
        default=[],
        help="Validate a non-authoritative candidate adoption review package. Repeatable.",
    )
    parser.add_argument(
        "--comparison-artifact-dir",
        action="append",
        default=[],
        help="Validate a diagnostic multi-candidate comparison artifact. Repeatable.",
    )
    parser.add_argument(
        "--judge-ablation-plan-dir",
        action="append",
        default=[],
        help="Validate a dual-policy judge ablation plan directory. Repeatable.",
    )
    parser.add_argument(
        "--judge-artifact-dir",
        action="append",
        default=[],
        help="Validate an authoritative judge artifact directory. Repeatable.",
    )
    parser.add_argument(
        "--paper-doc",
        action="append",
        default=[],
        help="Paper-facing markdown/text file to scan for forbidden claims. Repeatable.",
    )
    parser.add_argument(
        "--include-standard-paper-docs",
        action="store_true",
        help=(
            "Also scan the standard paper-facing docs, context hub docs, prompt library, "
            "PyCharm AI Assistant rules, and generated paper evidence table."
        ),
    )
    parser.add_argument(
        "--promotion-doc",
        action="append",
        default=[],
        help=("Markdown document containing a paper artifact promotion registry. Repeatable."),
    )
    parser.add_argument(
        "--fail-on-open-risks",
        action="store_true",
        help="Fail if docs/Risks.md still contains open risks.",
    )
    parser.add_argument(
        "--fail-on-actionable-risks",
        action="store_true",
        help=(
            "Fail only if docs/Risks.md still contains open risks categorized "
            "as actionable_nonhuman."
        ),
    )
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    report = check_release_readiness(
        benchmark_artifact_dirs=args.benchmark_artifact_dir,
        dual_policy_pairs=args.dual_policy_pair,
        comparison_artifact_dirs=args.comparison_artifact_dir,
        candidate_review_dirs=args.candidate_review_dir,
        judge_ablation_plan_dirs=args.judge_ablation_plan_dir,
        judge_artifact_dirs=args.judge_artifact_dir,
        paper_docs=args.paper_doc,
        promotion_docs=args.promotion_doc,
        fail_on_open_risks=args.fail_on_open_risks,
        fail_on_actionable_risks=args.fail_on_actionable_risks,
        include_standard_paper_docs=args.include_standard_paper_docs,
    )
    if args.json:
        print(json.dumps(report.as_dict(), ensure_ascii=False, indent=2))
    else:
        print(f"ok={report.ok}")
        print(f"open_risks={report.checked.get('open_risks')}")
        print(f"actionable_open_risks={report.checked.get('actionable_open_risks')}")
        for issue in report.issues:
            path = f" [{issue.path}]" if issue.path else ""
            print(f"{issue.severity}:{issue.code}{path}: {issue.message}")
    raise SystemExit(0 if report.ok else 1)


if __name__ == "__main__":
    main()
