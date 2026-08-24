from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Literal

CandidateConsistencySeverity = Literal["warning", "error"]
GOLD_LEAKAGE_KEYS = {
    "case_id",
    "id",
    "audit_id",
    "source_id",
    "gold_sql",
    "expected_sql",
    "gold_result_hash",
    "gold_result_preview",
    "expected_result_hash",
    "expected_result_preview",
    "execution_correct",
    "result_match",
    "ok",
    "error",
    "benchmark_error",
    "strict_policy_label",
    "semantic_policy_label",
    "combined_label",
    "semantic_business_correct",
    "judge_label",
}
RUNTIME_CANDIDATE_KEYS = {
    "candidate_id",
    "sql",
    "generated_sql",
    "valid_sql",
    "execution_passed",
    "execution_ok",
    "result_hash",
    "execution_result_hash",
}


@dataclass(slots=True)
class SqlCandidate:
    candidate_id: str
    sql: str | None
    valid_sql: bool | None = None
    execution_passed: bool | None = None
    result_hash: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_record(cls, record: dict[str, Any], index: int) -> "SqlCandidate":
        return cls(
            candidate_id=str(record.get("candidate_id") or f"candidate_{index}"),
            sql=record.get("sql") or record.get("generated_sql"),
            valid_sql=record.get("valid_sql"),
            execution_passed=record.get("execution_passed") or record.get("execution_ok"),
            result_hash=record.get("result_hash") or record.get("execution_result_hash"),
            metadata={
                key: value
                for key, value in record.items()
                if key not in RUNTIME_CANDIDATE_KEYS and key not in GOLD_LEAKAGE_KEYS
            },
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "sql": self.sql,
            "valid_sql": self.valid_sql,
            "execution_passed": self.execution_passed,
            "result_hash": self.result_hash,
            "metadata": dict(self.metadata),
        }


@dataclass(slots=True)
class CandidateConsistencyIssue:
    code: str
    message: str
    severity: CandidateConsistencySeverity = "error"
    candidate_ids: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "severity": self.severity,
            "candidate_ids": list(self.candidate_ids),
        }


@dataclass(slots=True)
class CandidateConsistencyReport:
    passed: bool
    selected_candidate_id: str | None
    issues: list[CandidateConsistencyIssue]
    signatures: dict[str, dict[str, Any]]

    def as_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "selected_candidate_id": self.selected_candidate_id,
            "issues": [issue.as_dict() for issue in self.issues],
            "signatures": {key: dict(value) for key, value in self.signatures.items()},
        }


def analyze_candidate_consistency(
    candidates: list[SqlCandidate | dict[str, Any]],
) -> CandidateConsistencyReport:
    """Compare SQL candidates using runtime-only evidence.

    This module intentionally does not accept gold SQL, benchmark case IDs, or exact
    correctness labels. It compares candidate SQL signatures and optional result
    hashes produced by executing the candidates.
    """

    normalized = [
        (
            candidate
            if isinstance(candidate, SqlCandidate)
            else SqlCandidate.from_record(candidate, index)
        )
        for index, candidate in enumerate(candidates)
    ]
    issues: list[CandidateConsistencyIssue] = []
    signatures = {
        candidate.candidate_id: _sql_signature(candidate.sql)
        for candidate in normalized
        if candidate.sql
    }

    viable = [
        candidate
        for candidate in normalized
        if candidate.sql
        and candidate.valid_sql is not False
        and candidate.execution_passed is not False
    ]

    if not normalized:
        return CandidateConsistencyReport(
            passed=False,
            selected_candidate_id=None,
            issues=[
                CandidateConsistencyIssue(
                    code="NO_CANDIDATES",
                    message="No SQL candidates were provided for consistency analysis.",
                )
            ],
            signatures=signatures,
        )

    if len(viable) == 1:
        issues.append(
            CandidateConsistencyIssue(
                code="SINGLE_VIABLE_CANDIDATE",
                message="Only one viable SQL candidate is available; no cross-candidate agreement can be measured.",
                severity="warning",
                candidate_ids=[viable[0].candidate_id],
            )
        )

    if not viable:
        return CandidateConsistencyReport(
            passed=False,
            selected_candidate_id=None,
            issues=[
                CandidateConsistencyIssue(
                    code="NO_VIABLE_CANDIDATES",
                    message="No candidate has enough runtime evidence to be considered viable.",
                    candidate_ids=[candidate.candidate_id for candidate in normalized],
                )
            ],
            signatures=signatures,
        )

    _add_signature_disagreement_issues(viable, signatures, issues)
    _add_result_hash_disagreement_issue(viable, issues)

    hard_issues = [issue for issue in issues if issue.severity == "error"]
    selected_candidate_id = _select_candidate(viable)
    return CandidateConsistencyReport(
        passed=not hard_issues,
        selected_candidate_id=selected_candidate_id,
        issues=issues,
        signatures=signatures,
    )


def _add_signature_disagreement_issues(
    candidates: list[SqlCandidate],
    signatures: dict[str, dict[str, Any]],
    issues: list[CandidateConsistencyIssue],
) -> None:
    dimensions = {
        "tables": "CANDIDATE_TABLE_DISAGREEMENT",
        "aggregations": "CANDIDATE_AGGREGATION_DISAGREEMENT",
        "group_columns": "CANDIDATE_GROUPING_DISAGREEMENT",
        "where_fingerprint": "CANDIDATE_FILTER_DISAGREEMENT",
    }
    for key, code in dimensions.items():
        values = {
            _hashable_signature_value(signatures.get(candidate.candidate_id, {}).get(key))
            for candidate in candidates
        }
        if len(values) > 1:
            issues.append(
                CandidateConsistencyIssue(
                    code=code,
                    message=f"Viable SQL candidates disagree on {key}.",
                    candidate_ids=[candidate.candidate_id for candidate in candidates],
                )
            )


def _add_result_hash_disagreement_issue(
    candidates: list[SqlCandidate],
    issues: list[CandidateConsistencyIssue],
) -> None:
    hashed = [candidate for candidate in candidates if candidate.result_hash]
    if len(hashed) < 2:
        return
    if len({candidate.result_hash for candidate in hashed}) > 1:
        issues.append(
            CandidateConsistencyIssue(
                code="CANDIDATE_RESULT_HASH_DISAGREEMENT",
                message="Viable SQL candidates produced different execution result hashes.",
                candidate_ids=[candidate.candidate_id for candidate in hashed],
            )
        )


def _select_candidate(candidates: list[SqlCandidate]) -> str | None:
    hash_counts = Counter(
        candidate.result_hash for candidate in candidates if candidate.result_hash
    )
    if hash_counts:
        result_hash, count = hash_counts.most_common(1)[0]
        if count >= 2:
            for candidate in candidates:
                if candidate.result_hash == result_hash:
                    return candidate.candidate_id
    return candidates[0].candidate_id if candidates else None


def _sql_signature(sql: str | None) -> dict[str, Any]:
    if not sql:
        return {
            "tables": [],
            "columns": [],
            "aggregations": [],
            "group_columns": [],
            "where_fingerprint": "",
        }
    try:
        import sqlglot
        from sqlglot import exp

        parsed = sqlglot.parse_one(sql, read="sqlite")
        tables = sorted({table.name.lower() for table in parsed.find_all(exp.Table) if table.name})
        columns = sorted(
            {column.name.lower() for column in parsed.find_all(exp.Column) if column.name}
        )
        aggregations = sorted(
            node.key.lower() for node in parsed.find_all(exp.AggFunc) if getattr(node, "key", None)
        )
        group = parsed.args.get("group")
        group_columns: list[str] = []
        if group is not None:
            group_columns = sorted(
                column.name.lower() for column in group.find_all(exp.Column) if column.name
            )
        where = parsed.args.get("where")
        where_fingerprint = _normalize_sql_fragment(
            where.sql(dialect="sqlite") if where is not None else ""
        )
        return {
            "tables": tables,
            "columns": columns,
            "aggregations": aggregations,
            "group_columns": group_columns,
            "where_fingerprint": where_fingerprint,
        }
    except Exception:
        return _fallback_signature(sql)


def _fallback_signature(sql: str) -> dict[str, Any]:
    normalized = _normalize_sql_fragment(sql)
    return {
        "tables": [],
        "columns": [],
        "aggregations": sorted(
            function
            for function in ("count(", "sum(", "avg(", "min(", "max(")
            if function in normalized
        ),
        "group_columns": ["__present__"] if "group by" in normalized else [],
        "where_fingerprint": (
            normalized.split(" where ", 1)[1].split(" group by ", 1)[0]
            if " where " in normalized
            else ""
        ),
    }


def _normalize_sql_fragment(value: str) -> str:
    return " ".join(str(value or "").lower().split())


def _hashable_signature_value(value: Any) -> Any:
    if isinstance(value, list):
        return tuple(value)
    if isinstance(value, dict):
        return tuple(sorted(value.items()))
    return value
