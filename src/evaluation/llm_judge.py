from __future__ import annotations

import re
import csv
import http.client
import json
import os
import time
import urllib.error
import urllib.request
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol

from src.config.paths import RESULTS_DIR
from src.evaluation.artifact_analysis import locate_benchmark_artifact
from src.evaluation.dataset_loader import read_json, read_jsonl, write_json, write_jsonl

PROMPT_VERSION = "phase16_sql_business_logic_v1"
JUDGE_POLICY_SEMANTIC = "semantic_user_question"
JUDGE_POLICY_STRICT = "strict_reference"
SUPPORTED_JUDGE_POLICIES = {JUDGE_POLICY_SEMANTIC, JUDGE_POLICY_STRICT}
REDACTED_PAYLOAD_INCLUDED_FIELDS = [
    "case_id",
    "question",
    "expected_action",
    "actual_action",
    "intent",
    "category",
    "difficulty",
    "generated_sql",
    "gold_sql",
    "valid_sql",
    "execution_correct",
    "benchmark_error",
    "validation_issues",
    "execution_result_hash",
    "gold_result_hash",
]
REDACTED_PAYLOAD_EXCLUDED_FIELDS = [
    "raw_database_rows",
    "execution_result_preview",
    "gold_result_preview",
    "full_prompt",
    "raw_model_response",
]


@dataclass(frozen=True, slots=True)
class JudgeResult:
    case_id: str
    provider: str
    model: str
    prompt_version: str
    judge_policy: str
    verdict: str
    semantic_business_correct: bool | None
    score: float | None
    reason: str
    authoritative: bool
    redacted: bool
    generated_sql_hash: str | None = None
    gold_sql_hash: str | None = None
    metric_correct: bool | None = None
    filter_correct: bool | None = None
    join_logic_correct: bool | None = None
    aggregation_correct: bool | None = None
    needs_human_review: bool | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: float = 0.0
    raw_provider_model: str | None = None
    raw_provider_verdict: str | None = None
    reasoning_tokens: int = 0
    reasoning_details_present: bool = False


@dataclass(frozen=True, slots=True)
class JudgeArtifactIssue:
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


@dataclass(frozen=True, slots=True)
class JudgeArtifactValidationReport:
    ok: bool
    issues: list[JudgeArtifactIssue] = field(default_factory=list)
    checked: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "issues": [issue.as_dict() for issue in self.issues],
            "checked": self.checked,
        }


class JudgeProvider(Protocol):
    provider_name: str
    model_name: str
    judge_policy: str

    def judge(self, record: dict[str, Any]) -> JudgeResult: ...


def normalize_sql(sql: str | None) -> str:
    if not sql:
        return ""
    stripped = re.sub(r"\s*;\s*$", "", sql.strip())
    compact = re.sub(r"\s+", " ", stripped)
    return compact.lower()


def _short_hash(text: str | None) -> str | None:
    if not text:
        return None
    import hashlib

    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _normalize_judge_policy(value: str | None) -> str:
    normalized = (value or JUDGE_POLICY_SEMANTIC).strip().lower().replace("-", "_")
    aliases = {
        "semantic": JUDGE_POLICY_SEMANTIC,
        "user_question": JUDGE_POLICY_SEMANTIC,
        "semantic_user_question": JUDGE_POLICY_SEMANTIC,
        "strict": JUDGE_POLICY_STRICT,
        "reference": JUDGE_POLICY_STRICT,
        "strict_reference": JUDGE_POLICY_STRICT,
    }
    policy = aliases.get(normalized)
    if policy is None:
        raise ValueError(
            f"Unsupported judge policy '{value}'. Supported policies: semantic, strict."
        )
    return policy


class MockJudgeProvider:
    """Deterministic scaffold provider that avoids inventing semantic labels.

    This provider is intentionally conservative. It marks exact SQL matches as
    correct, invalid/missing SQL as incorrect, and valid result mismatches as
    requiring independent semantic review.
    """

    provider_name = "mock"
    model_name = "deterministic_exact_match_v0"

    def __init__(self, *, judge_policy: str = JUDGE_POLICY_SEMANTIC) -> None:
        self.judge_policy = _normalize_judge_policy(judge_policy)

    def judge(self, record: dict[str, Any]) -> JudgeResult:
        case_id = str(record.get("id") or record.get("case_id") or "")
        generated_sql = record.get("generated_sql")
        gold_sql = record.get("gold_sql")
        valid_sql = bool(record.get("valid_sql"))
        error = str(record.get("error") or "")

        generated_norm = normalize_sql(generated_sql)
        gold_norm = normalize_sql(gold_sql)

        if generated_norm and gold_norm and generated_norm == gold_norm:
            verdict = "exact_sql_match"
            semantic_business_correct: bool | None = True
            score: float | None = 1.0
            reason = "Generated SQL matches the gold SQL after whitespace/case normalization."
        elif not generated_norm:
            verdict = "missing_sql"
            semantic_business_correct = False
            score = 0.0
            reason = "No generated SQL exists, so the query cannot satisfy the requested business logic."
        elif not valid_sql:
            verdict = "invalid_sql"
            semantic_business_correct = False
            score = 0.0
            reason = "Generated SQL did not pass validation/execution, so it cannot be business-correct."
        elif self.judge_policy == JUDGE_POLICY_STRICT and error == "RESULT_MISMATCH":
            verdict = "strict_reference_mismatch"
            semantic_business_correct = False
            score = 0.0
            reason = "Generated SQL is valid but does not match the strict reference result/shape."
        elif error == "RESULT_MISMATCH":
            verdict = "requires_semantic_review"
            semantic_business_correct = None
            score = None
            reason = "Valid SQL produced a result mismatch. The mock judge does not infer semantic correctness."
        else:
            verdict = "unjudged"
            semantic_business_correct = None
            score = None
            reason = "The mock judge only labels exact matches, missing SQL, invalid SQL, and valid result mismatches."

        return JudgeResult(
            case_id=case_id,
            provider=self.provider_name,
            model=self.model_name,
            prompt_version=PROMPT_VERSION,
            judge_policy=self.judge_policy,
            verdict=verdict,
            semantic_business_correct=semantic_business_correct,
            score=score,
            reason=reason,
            authoritative=False,
            redacted=True,
            generated_sql_hash=_short_hash(generated_sql),
            gold_sql_hash=_short_hash(gold_sql),
            needs_human_review=semantic_business_correct is None,
        )


def _redacted_judge_payload(record: dict[str, Any]) -> dict[str, Any]:
    attempts = record.get("attempts") or []
    validation_issues = record.get("validation_issues") or []
    if not validation_issues and attempts:
        latest_attempt = attempts[-1] if isinstance(attempts[-1], dict) else {}
        validation_issues = latest_attempt.get("validation_errors") or []
    return {
        "case_id": record.get("id") or record.get("case_id"),
        "question": record.get("question_fa") or record.get("question"),
        "expected_action": record.get("expected_action"),
        "actual_action": record.get("actual_action"),
        "intent": record.get("intent"),
        "category": record.get("category"),
        "difficulty": record.get("difficulty"),
        "generated_sql": record.get("generated_sql"),
        "gold_sql": record.get("gold_sql"),
        "valid_sql": record.get("valid_sql"),
        "execution_correct": record.get("execution_correct"),
        "benchmark_error": record.get("error"),
        "validation_issues": validation_issues,
        "execution_result_hash": record.get("execution_result_hash")
        or record.get("result_hash"),
        "gold_result_hash": record.get("gold_result_hash"),
    }


def _redaction_policy_summary() -> dict[str, Any]:
    return {
        "redaction_applied": True,
        "included_fields": REDACTED_PAYLOAD_INCLUDED_FIELDS,
        "excluded_fields": REDACTED_PAYLOAD_EXCLUDED_FIELDS,
        "raw_rows_sent": False,
        "result_previews_sent": False,
        "prompt_response_trace_sent": False,
        "note": (
            "Cloud judge payloads include question, SQL, validation metadata and result hashes only. "
            "Raw database rows, result previews and full prompt/raw model-response traces are excluded."
        ),
    }


def validate_judge_artifact(
    judge_dir: str | Path,
    *,
    require_authoritative: bool = False,
) -> JudgeArtifactValidationReport:
    root = Path(judge_dir)
    paths = {
        "summary": root / "judge_summary.json",
        "judgments": root / "judgments.jsonl",
        "costs": root / "judge_costs.json",
        "semantic_summary": root / "semantic_business_summary.csv",
        "reasoning": root / "judge_reasoning.md",
    }
    issues: list[JudgeArtifactIssue] = []
    checked: dict[str, Any] = {
        "judge_dir": str(root),
        "required_files": {key: str(path) for key, path in paths.items()},
        "require_authoritative": require_authoritative,
    }
    missing = [key for key, path in paths.items() if not path.exists()]
    checked["missing_files"] = missing
    for key in missing:
        _append_judge_artifact_issue(
            issues,
            "JUDGE_ARTIFACT_FILE_MISSING",
            f"Judge artifact is missing {paths[key].name}.",
            paths[key],
        )
    if any(key in missing for key in ("summary", "judgments", "costs")):
        return JudgeArtifactValidationReport(ok=False, issues=issues, checked=checked)

    try:
        summary = read_json(paths["summary"])
        costs = read_json(paths["costs"])
        judgments = read_jsonl(paths["judgments"])
    except (OSError, json.JSONDecodeError) as exc:
        _append_judge_artifact_issue(
            issues,
            "JUDGE_ARTIFACT_READ_FAILED",
            f"Could not read judge artifact: {exc}",
            root,
        )
        return JudgeArtifactValidationReport(ok=False, issues=issues, checked=checked)

    if not isinstance(summary, dict) or not isinstance(costs, dict):
        _append_judge_artifact_issue(
            issues,
            "JUDGE_ARTIFACT_JSON_INVALID",
            "Judge summary and costs must be JSON objects.",
            root,
        )
        return JudgeArtifactValidationReport(ok=False, issues=issues, checked=checked)

    _validate_judge_summary_metadata(
        summary, judgments, require_authoritative, issues, paths
    )
    _validate_judge_cost_metadata(summary, costs, issues, paths)
    _validate_judge_counts(summary, judgments, issues, paths)

    checked.update(
        {
            "provider": summary.get("provider"),
            "model": summary.get("model"),
            "prompt_version": summary.get("prompt_version"),
            "judge_policy": summary.get("judge_policy"),
            "authoritative": summary.get("authoritative"),
            "total_judged": summary.get("total_judged"),
            "judgment_rows": len(judgments),
            "cost_authoritative": costs.get("cost_authoritative"),
        }
    )
    return JudgeArtifactValidationReport(ok=not issues, issues=issues, checked=checked)


def _validate_judge_summary_metadata(
    summary: dict[str, Any],
    judgments: list[dict[str, Any]],
    require_authoritative: bool,
    issues: list[JudgeArtifactIssue],
    paths: dict[str, Path],
) -> None:
    required_fields = [
        "generated_at",
        "provider",
        "model",
        "prompt_version",
        "judge_policy",
        "authoritative",
        "authoritative_judgments",
        "non_authoritative_judgments",
        "total_predictions",
        "total_judged",
        "verdict_counts",
        "semantic_business_counts",
        "redaction_policy",
        "anti_fake_policy",
    ]
    missing = [field for field in required_fields if field not in summary]
    if missing:
        _append_judge_artifact_issue(
            issues,
            "JUDGE_SUMMARY_FIELD_MISSING",
            f"Judge summary is missing required fields: {', '.join(missing)}.",
            paths["summary"],
        )

    provider = str(summary.get("provider") or "").lower()
    if require_authoritative and summary.get("authoritative") is not True:
        _append_judge_artifact_issue(
            issues,
            "JUDGE_ARTIFACT_NOT_AUTHORITATIVE",
            "Paper-facing judge artifacts must be authoritative.",
            paths["summary"],
        )
    if provider == "mock" and summary.get("authoritative") is True:
        _append_judge_artifact_issue(
            issues,
            "MOCK_JUDGE_AUTHORITATIVE",
            "Mock judge outputs must not be marked authoritative.",
            paths["summary"],
        )

    authoritative_rows = sum(1 for row in judgments if row.get("authoritative") is True)
    non_authoritative_rows = len(judgments) - authoritative_rows
    if _as_int(summary.get("authoritative_judgments")) != authoritative_rows:
        _append_judge_artifact_issue(
            issues,
            "JUDGE_AUTHORITATIVE_COUNT_MISMATCH",
            "authoritative_judgments does not match judgment rows.",
            paths["summary"],
        )
    if _as_int(summary.get("non_authoritative_judgments")) != non_authoritative_rows:
        _append_judge_artifact_issue(
            issues,
            "JUDGE_NON_AUTHORITATIVE_COUNT_MISMATCH",
            "non_authoritative_judgments does not match judgment rows.",
            paths["summary"],
        )
    if summary.get("authoritative") is True and non_authoritative_rows:
        _append_judge_artifact_issue(
            issues,
            "JUDGE_AUTHORITATIVE_FLAG_MISMATCH",
            "authoritative=true requires every judgment row to be authoritative.",
            paths["summary"],
        )

    redaction = summary.get("redaction_policy")
    if (
        not isinstance(redaction, dict)
        or redaction.get("redaction_applied") is not True
    ):
        _append_judge_artifact_issue(
            issues,
            "JUDGE_REDACTION_POLICY_MISSING",
            "Judge summary must record an applied redaction policy.",
            paths["summary"],
        )
    elif (
        redaction.get("raw_rows_sent") is not False
        or redaction.get("result_previews_sent") is not False
        or redaction.get("prompt_response_trace_sent") is not False
    ):
        _append_judge_artifact_issue(
            issues,
            "JUDGE_REDACTION_POLICY_UNSAFE",
            "Judge redaction policy must exclude raw rows, result previews, and prompt traces.",
            paths["summary"],
        )

    if not str(summary.get("anti_fake_policy") or "").strip():
        _append_judge_artifact_issue(
            issues,
            "JUDGE_ANTI_FAKE_POLICY_MISSING",
            "Judge summary must include an anti-fake policy statement.",
            paths["summary"],
        )


def _validate_judge_cost_metadata(
    summary: dict[str, Any],
    costs: dict[str, Any],
    issues: list[JudgeArtifactIssue],
    paths: dict[str, Path],
) -> None:
    for cost_field in ("provider", "model", "judge_policy"):
        if costs.get(cost_field) != summary.get(cost_field):
            _append_judge_artifact_issue(
                issues,
                "JUDGE_COST_METADATA_MISMATCH",
                f"judge_costs.json field {cost_field!r} does not match judge_summary.json.",
                paths["costs"],
            )
    for cost_field in (
        "input_tokens",
        "output_tokens",
        "reasoning_tokens",
        "estimated_cost_usd",
    ):
        if not isinstance(costs.get(cost_field), int | float):
            _append_judge_artifact_issue(
                issues,
                "JUDGE_COST_FIELD_MISSING",
                f"judge_costs.json must record numeric {cost_field}.",
                paths["costs"],
            )
    provider = str(summary.get("provider") or "").lower()
    if provider != "mock" and costs.get("cost_authoritative") is not True:
        _append_judge_artifact_issue(
            issues,
            "JUDGE_COST_NOT_AUTHORITATIVE",
            "Live judge artifacts must mark token/cost metadata authoritative.",
            paths["costs"],
        )


def _validate_judge_counts(
    summary: dict[str, Any],
    judgments: list[dict[str, Any]],
    issues: list[JudgeArtifactIssue],
    paths: dict[str, Path],
) -> None:
    if _as_int(summary.get("total_judged")) != len(judgments):
        _append_judge_artifact_issue(
            issues,
            "JUDGE_TOTAL_COUNT_MISMATCH",
            "total_judged does not match judgments.jsonl row count.",
            paths["summary"],
        )

    verdict_counts = Counter(str(row.get("verdict") or "unknown") for row in judgments)
    summary_verdict_counts = summary.get("verdict_counts")
    if isinstance(summary_verdict_counts, dict):
        for verdict in set(verdict_counts) | set(summary_verdict_counts):
            if _as_int(summary_verdict_counts.get(verdict)) != verdict_counts.get(
                verdict, 0
            ):
                _append_judge_artifact_issue(
                    issues,
                    "JUDGE_VERDICT_COUNT_MISMATCH",
                    f"verdict_counts[{verdict!r}] does not match judgments.jsonl.",
                    paths["summary"],
                )

    semantic_counts = _semantic_counts_from_judgments(judgments)
    summary_semantic_counts = summary.get("semantic_business_counts")
    if isinstance(summary_semantic_counts, dict):
        for key in set(semantic_counts) | set(summary_semantic_counts):
            if _as_int(summary_semantic_counts.get(key)) != semantic_counts.get(key, 0):
                _append_judge_artifact_issue(
                    issues,
                    "JUDGE_SEMANTIC_COUNT_MISMATCH",
                    f"semantic_business_counts[{key!r}] does not match judgments.jsonl.",
                    paths["summary"],
                )

    for summary_field in ("provider", "model", "prompt_version", "judge_policy"):
        expected = summary.get(summary_field)
        if expected is None:
            continue
        mismatches = [
            row.get("case_id")
            for row in judgments
            if row.get(summary_field) != expected
        ]
        if mismatches:
            _append_judge_artifact_issue(
                issues,
                "JUDGE_ROW_METADATA_MISMATCH",
                f"Judgment row metadata for {summary_field!r} does not match summary.",
                paths["judgments"],
            )


def _semantic_counts_from_judgments(judgments: list[dict[str, Any]]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for row in judgments:
        verdict = str(row.get("verdict") or "")
        if verdict in {"provider_error", "provider_parse_error"}:
            counts[verdict] += 1
        elif row.get("semantic_business_correct") is True:
            counts["correct"] += 1
        elif row.get("semantic_business_correct") is False:
            counts["incorrect"] += 1
        else:
            counts["unjudged"] += 1
    return counts


def _as_int(value: Any) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    return 0


def _append_judge_artifact_issue(
    issues: list[JudgeArtifactIssue],
    code: str,
    message: str,
    path: Path,
) -> None:
    issues.append(JudgeArtifactIssue(code=code, message=message, path=str(path)))


def _strip_code_fence(text: str | None) -> str:
    if text is None:
        return ""
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped, flags=re.IGNORECASE)
        stripped = re.sub(r"\s*```$", "", stripped)
    return stripped.strip()


def _parse_provider_json(text: str) -> dict[str, Any]:
    stripped = _strip_code_fence(text)
    if not stripped:
        raise json.JSONDecodeError("empty provider content", "", 0)
    try:
        return json.loads(stripped)
    except json.JSONDecodeError as original_exc:
        decoder = json.JSONDecoder()
        for index, char in enumerate(stripped):
            if char != "{":
                continue
            try:
                parsed, _ = decoder.raw_decode(stripped[index:])
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                return parsed
        raise original_exc


def _coerce_optional_bool(value: Any) -> bool | None:
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "yes", "correct"}:
            return True
        if lowered in {"false", "no", "incorrect"}:
            return False
    return None


def _coerce_optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _canonical_provider_verdict(
    raw_verdict: Any,
    semantic_business_correct: bool | None,
    needs_human_review: bool | None,
    *,
    valid_sql: bool | None,
) -> tuple[str, bool | None, bool]:
    """Map free-form provider labels to report-stable categories.

    Provider-specific labels are useful evidence, but summary tables must not
    treat arbitrary words like "partial_match" or "disapproved" as final paper
    metrics. Partial labels defer to the provider's explicit semantic boolean:
    a query that answers the user's question is business-correct even if it
    differs from the gold SQL or omits gold-only support columns.
    """

    raw = str(raw_verdict or "").strip().lower()
    normalized = re.sub(r"[^a-z0-9]+", "_", raw).strip("_")

    if normalized in {
        "partial",
        "partial_match",
        "partially_correct",
        "partial_business_match",
    }:
        if semantic_business_correct is True:
            return "business_correct", True, bool(needs_human_review)
        if semantic_business_correct is False:
            return "business_incorrect", False, bool(needs_human_review)
        return "partial_business_match", None, True

    if normalized in {
        "ambiguous",
        "uncertain",
        "unknown",
        "unjudged",
        "disapproved",
        "requires_review",
        "requires_semantic_review",
        "needs_human_review",
    }:
        return "requires_semantic_review", None, True

    if normalized in {"invalid", "invalid_sql", "missing_sql"}:
        if valid_sql is False:
            return (
                "invalid_sql" if normalized != "missing_sql" else "missing_sql",
                False,
                False,
            )
        if semantic_business_correct is False:
            return "business_incorrect", False, bool(needs_human_review)
        return "requires_semantic_review", None, True

    if normalized in {"fail", "failed", "incorrect", "wrong", "business_incorrect"}:
        return "business_incorrect", False, bool(needs_human_review)

    if normalized in {
        "pass",
        "passed",
        "correct",
        "ok",
        "business_correct",
        "exact_sql_match",
    }:
        if semantic_business_correct is True:
            return "business_correct", True, bool(needs_human_review)
        if semantic_business_correct is False:
            return "business_incorrect", False, bool(needs_human_review)
        return "requires_semantic_review", None, True

    if semantic_business_correct is True:
        return "business_correct", True, bool(needs_human_review)
    if semantic_business_correct is False:
        return "business_incorrect", False, bool(needs_human_review)
    return "requires_semantic_review", None, True


class OpenRouterJudgeProvider:
    provider_name = "openrouter"

    def __init__(
        self,
        *,
        model_name: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        app_url: str | None = None,
        app_title: str | None = None,
        timeout_seconds: int = 120,
        max_retries: int | None = None,
        reasoning_enabled: bool | None = None,
        judge_policy: str = JUDGE_POLICY_SEMANTIC,
    ) -> None:
        self.model_name = (
            model_name
            or os.getenv("VTD_OPENROUTER_JUDGE_MODEL")
            or os.getenv("OPENROUTER_JUDGE_MODEL")
            or "qwen/qwen3.6-plus"
        )
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self.base_url = (
            base_url
            or os.getenv("OPENROUTER_BASE_URL")
            or "https://openrouter.ai/api/v1"
        ).rstrip("/")
        self.app_url = (
            app_url
            or os.getenv("OPENROUTER_HTTP_REFERER")
            or "https://github.com/local/ADHD-VTD"
        )
        self.app_title = (
            app_title or os.getenv("OPENROUTER_APP_TITLE") or "ADHD-VTD Phase16 Judge"
        )
        self.timeout_seconds = timeout_seconds
        self.max_retries = (
            max_retries
            if max_retries is not None
            else int(os.getenv("VTD_OPENROUTER_JUDGE_RETRIES", "2"))
        )
        if reasoning_enabled is None:
            reasoning_enabled = os.getenv(
                "VTD_OPENROUTER_JUDGE_REASONING", ""
            ).strip().lower() in {
                "1",
                "true",
                "yes",
                "on",
            }
        self.reasoning_enabled = reasoning_enabled
        self.judge_policy = _normalize_judge_policy(judge_policy)

    def judge(self, record: dict[str, Any]) -> JudgeResult:
        case_id = str(record.get("id") or record.get("case_id") or "")
        generated_sql = record.get("generated_sql")
        gold_sql = record.get("gold_sql")
        if not self.api_key:
            return JudgeResult(
                case_id=case_id,
                provider=self.provider_name,
                model=self.model_name,
                prompt_version=PROMPT_VERSION,
                judge_policy=self.judge_policy,
                verdict="provider_not_configured",
                semantic_business_correct=None,
                score=None,
                reason="OPENROUTER_API_KEY is not set; no live judgment was requested.",
                authoritative=False,
                redacted=True,
                generated_sql_hash=_short_hash(generated_sql),
                gold_sql_hash=_short_hash(gold_sql),
                needs_human_review=True,
            )

        if self.judge_policy == JUDGE_POLICY_STRICT:
            system_policy = (
                "Judge strict reference correctness against the user's question and the gold SQL/reference output "
                "contract. Gold SQL is the reference implementation for this strict policy. Missing reference "
                "support columns, different grouping/filter/order/threshold logic, or result-shape mismatches should "
                "be marked incorrect unless they are clearly irrelevant formatting differences. Return JSON only. "
                "Do not assume hidden data. If the artifact is insufficient, set semantic_business_correct to null "
                "and needs_human_review to true."
            )
            semantic_rule = (
                "Under strict_reference policy, true only when the generated SQL satisfies the reference-level "
                "business/output contract represented by the question and gold SQL. false when the generated SQL "
                "answers only the core intent but misses reference-required columns, filters, grouping, ordering, "
                "thresholds, or result shape."
            )
            verdict_policy = {
                "business_correct": "The generated SQL satisfies the strict reference-level business/output contract.",
                "partial_business_match": (
                    "The core intent may be present, but the generated SQL is incomplete relative to the strict "
                    "reference contract and needs review."
                ),
                "business_incorrect": (
                    "The generated SQL is valid or parseable but fails the strict reference-level metric, filter, "
                    "grouping, ordering, threshold, table, or output-shape contract."
                ),
            }
        else:
            system_policy = (
                "Judge semantic correctness against the user's question, not against exact gold SQL shape. Gold SQL "
                "is a reference implementation, not a mandatory output schema. Extra harmless columns or parameters "
                "are allowed, and missing gold-only support columns are allowed, when the generated SQL still gives "
                "the user the answer they asked for. Return JSON only. Do not assume hidden data. If the SQL is valid "
                "but whether it answers the user's question cannot be determined from the provided artifact, set "
                "semantic_business_correct to null and needs_human_review to true."
            )
            semantic_rule = (
                "Under semantic_user_question policy, true only when the generated SQL answers the user's actual "
                "question. It may differ from gold SQL, include extra harmless output columns, or omit reference-only "
                "support columns. false when the core metric, filters, grouping, table, or time/value logic prevents "
                "the user from getting the requested answer. null when the artifact is insufficient."
            )
            verdict_policy = {
                "business_correct": (
                    "The user can answer their question from the generated SQL result, even if the SQL is not an "
                    "exact gold match."
                ),
                "partial_business_match": (
                    "Some relevant work is present, but a user-requested part is missing or the result is not "
                    "sufficient to answer the question without review."
                ),
                "business_incorrect": (
                    "The generated SQL is valid or parseable but answers the wrong business question, misses "
                    "required user-requested logic, or uses a wrong metric/filter/grouping/table."
                ),
            }

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a strict senior data analyst judging Persian text-to-SQL outputs. "
                    f"Judge policy: {self.judge_policy}. "
                    f"{system_policy} "
                    "Use one verdict from: business_correct, "
                    "business_incorrect, partial_business_match, invalid_sql, missing_sql, "
                    "requires_semantic_review."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "rubric": {
                            "score": "0 to 5, where 5 is perfect business logic and 0 is unusable/unsafe",
                            "judge_policy": self.judge_policy,
                            "semantic_business_correct": semantic_rule,
                            "verdict_policy": verdict_policy,
                            "required_json_keys": [
                                "verdict",
                                "semantic_business_correct",
                                "score",
                                "reason",
                                "metric_correct",
                                "filter_correct",
                                "join_logic_correct",
                                "aggregation_correct",
                                "needs_human_review",
                            ],
                        },
                        "artifact": _redacted_judge_payload(record),
                    },
                    ensure_ascii=False,
                ),
            },
        ]
        body = {
            "model": self.model_name,
            "messages": messages,
            "temperature": 0,
            "max_tokens": 700,
            "response_format": {"type": "json_object"},
        }
        if self.reasoning_enabled:
            body["reasoning"] = {"enabled": True}
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": self.app_url,
                "X-Title": self.app_title,
                "X-OpenRouter-Title": self.app_title,
            },
            method="POST",
        )
        response_payload: dict[str, Any] | None = None
        last_exc: Exception | None = None
        for attempt in range(max(1, self.max_retries + 1)):
            try:
                with urllib.request.urlopen(
                    request, timeout=self.timeout_seconds
                ) as response:
                    response_payload = json.loads(response.read().decode("utf-8"))
                break
            except (
                urllib.error.URLError,
                http.client.HTTPException,
                http.client.IncompleteRead,
                TimeoutError,
                json.JSONDecodeError,
                OSError,
            ) as exc:
                last_exc = exc
                if attempt < self.max_retries:
                    time.sleep(min(0.5 * (attempt + 1), 2.0))
                    continue
        if response_payload is None:
            exc = last_exc or RuntimeError("unknown provider error")
            return JudgeResult(
                case_id=case_id,
                provider=self.provider_name,
                model=self.model_name,
                prompt_version=PROMPT_VERSION,
                judge_policy=self.judge_policy,
                verdict="provider_error",
                semantic_business_correct=None,
                score=None,
                reason=f"OpenRouter request failed after {self.max_retries + 1} attempt(s): {type(exc).__name__}: {exc}",
                authoritative=False,
                redacted=True,
                generated_sql_hash=_short_hash(generated_sql),
                gold_sql_hash=_short_hash(gold_sql),
                needs_human_review=True,
            )

        message = response_payload.get("choices", [{}])[0].get("message", {})
        content = message.get("content", "")
        usage = response_payload.get("usage") or {}
        reasoning_tokens = int(
            usage.get("reasoning_tokens") or usage.get("reasoningTokens") or 0
        )
        try:
            parsed = _parse_provider_json(content)
        except (json.JSONDecodeError, TypeError) as exc:
            return JudgeResult(
                case_id=case_id,
                provider=self.provider_name,
                model=self.model_name,
                prompt_version=PROMPT_VERSION,
                judge_policy=self.judge_policy,
                verdict="provider_parse_error",
                semantic_business_correct=None,
                score=None,
                reason=f"Could not parse provider JSON response: {type(exc).__name__}",
                authoritative=False,
                redacted=True,
                generated_sql_hash=_short_hash(generated_sql),
                gold_sql_hash=_short_hash(gold_sql),
                needs_human_review=True,
                raw_provider_model=response_payload.get("model"),
                reasoning_tokens=reasoning_tokens,
                reasoning_details_present=bool(message.get("reasoning_details")),
            )

        semantic_business_correct = _coerce_optional_bool(
            parsed.get("semantic_business_correct")
        )
        needs_human_review = _coerce_optional_bool(parsed.get("needs_human_review"))
        verdict, semantic_business_correct, needs_human_review_bool = (
            _canonical_provider_verdict(
                parsed.get("verdict"),
                semantic_business_correct,
                needs_human_review,
                valid_sql=record.get("valid_sql"),
            )
        )
        return JudgeResult(
            case_id=case_id,
            provider=self.provider_name,
            model=self.model_name,
            prompt_version=PROMPT_VERSION,
            judge_policy=self.judge_policy,
            verdict=verdict,
            semantic_business_correct=semantic_business_correct,
            score=_coerce_optional_float(parsed.get("score")),
            reason=str(parsed.get("reason") or ""),
            authoritative=True,
            redacted=True,
            generated_sql_hash=_short_hash(generated_sql),
            gold_sql_hash=_short_hash(gold_sql),
            metric_correct=_coerce_optional_bool(parsed.get("metric_correct")),
            filter_correct=_coerce_optional_bool(parsed.get("filter_correct")),
            join_logic_correct=_coerce_optional_bool(parsed.get("join_logic_correct")),
            aggregation_correct=_coerce_optional_bool(
                parsed.get("aggregation_correct")
            ),
            needs_human_review=needs_human_review_bool,
            input_tokens=int(usage.get("prompt_tokens") or 0),
            output_tokens=int(usage.get("completion_tokens") or 0),
            estimated_cost_usd=0.0,
            raw_provider_model=response_payload.get("model"),
            raw_provider_verdict=str(parsed.get("verdict") or ""),
            reasoning_tokens=reasoning_tokens,
            reasoning_details_present=bool(message.get("reasoning_details")),
        )


def select_records_for_judging(
    predictions: list[dict[str, Any]],
    *,
    failures_only: bool = True,
    sample_size: int | None = None,
    case_ids: set[str] | None = None,
) -> list[dict[str, Any]]:
    selected = [
        record
        for record in predictions
        if (
            case_ids is None
            or str(record.get("id") or record.get("case_id") or "") in case_ids
        )
        and (
            not failures_only
            or not bool(
                record.get("ok")
                or record.get("execution_correct")
                or record.get("result_match")
            )
        )
    ]
    if sample_size is not None:
        selected = selected[: max(0, sample_size)]
    return selected


def _provider_from_name(
    name: str,
    *,
    model_name: str | None = None,
    reasoning_enabled: bool | None = None,
    judge_policy: str = JUDGE_POLICY_SEMANTIC,
) -> JudgeProvider:
    normalized = name.strip().lower()
    if normalized == "mock":
        return MockJudgeProvider(judge_policy=judge_policy)
    if normalized == "openrouter":
        return OpenRouterJudgeProvider(
            model_name=model_name,
            reasoning_enabled=reasoning_enabled,
            judge_policy=judge_policy,
        )
    raise ValueError(
        f"Unsupported judge provider '{name}'. Supported providers: mock, openrouter."
    )


def judge_benchmark_artifact(
    artifact_dir: str | Path,
    *,
    output_dir: str | Path | None = None,
    provider_name: str = "mock",
    judge_model: str | None = None,
    reasoning_enabled: bool | None = None,
    failures_only: bool = True,
    sample_size: int | None = None,
    case_ids: list[str] | None = None,
    judge_policy: str = JUDGE_POLICY_SEMANTIC,
) -> dict[str, Path]:
    artifact = locate_benchmark_artifact(artifact_dir)
    predictions = read_jsonl(artifact.predictions_path)
    summary = read_json(artifact.summary_path)
    provider = _provider_from_name(
        provider_name,
        model_name=judge_model,
        reasoning_enabled=reasoning_enabled,
        judge_policy=judge_policy,
    )

    records = select_records_for_judging(
        predictions,
        failures_only=failures_only,
        sample_size=sample_size,
        case_ids={str(case_id) for case_id in case_ids} if case_ids else None,
    )
    judgments = [asdict(provider.judge(record)) for record in records]

    if output_dir is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_root = RESULTS_DIR / "judgments" / timestamp
    else:
        output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    verdict_counts = Counter(row["verdict"] for row in judgments)
    authoritative_count = sum(
        1 for row in judgments if row.get("authoritative") is True
    )
    reasoning_tokens_total = sum(
        int(row.get("reasoning_tokens") or 0) for row in judgments
    )
    reasoning_details_count = sum(
        1 for row in judgments if row.get("reasoning_details_present")
    )
    correctness_counts = _semantic_counts_from_judgments(judgments)
    anti_fake_policy = (
        "Mock judgments are deterministic scaffold labels only. Valid SQL result mismatches remain unjudged until an independent semantic judge or human review runs."
        if provider.provider_name == "mock"
        else "OpenRouter judgments are live provider responses when authoritative=true. Provider errors and parse errors remain unjudged; live judgments are stored as evidence but should still be spot-checked before paper claims."
    )
    judge_summary = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source_artifact": str(artifact.root),
        "summary_path": str(artifact.summary_path),
        "predictions_path": str(artifact.predictions_path),
        "provider": provider.provider_name,
        "model": provider.model_name,
        "prompt_version": PROMPT_VERSION,
        "judge_policy": _normalize_judge_policy(judge_policy),
        "authoritative": bool(judgments) and authoritative_count == len(judgments),
        "authoritative_judgments": authoritative_count,
        "non_authoritative_judgments": len(judgments) - authoritative_count,
        "failures_only": failures_only,
        "sample_size": sample_size,
        "case_ids": case_ids,
        "total_predictions": len(predictions),
        "total_judged": len(judgments),
        "verdict_counts": dict(verdict_counts),
        "semantic_business_counts": dict(correctness_counts),
        "reasoning_tokens": reasoning_tokens_total,
        "reasoning_details_present": reasoning_details_count,
        "redaction_policy": _redaction_policy_summary(),
        "config": summary.get("config", {}),
        "anti_fake_policy": anti_fake_policy,
    }
    cost_summary = {
        "provider": provider.provider_name,
        "model": provider.model_name,
        "judge_policy": _normalize_judge_policy(judge_policy),
        "input_tokens": sum(int(row.get("input_tokens") or 0) for row in judgments),
        "output_tokens": sum(int(row.get("output_tokens") or 0) for row in judgments),
        "reasoning_tokens": sum(
            int(row.get("reasoning_tokens") or 0) for row in judgments
        ),
        "estimated_cost_usd": round(
            sum(float(row.get("estimated_cost_usd") or 0.0) for row in judgments), 8
        ),
        "cost_authoritative": provider.provider_name != "mock",
        "note": "Mock provider does not call an external model. OpenRouter token counts come from provider usage fields when available; dollar cost is not inferred unless provider billing data is added.",
    }

    judgments_path = write_jsonl(output_root / "judgments.jsonl", judgments)
    summary_path = write_json(output_root / "judge_summary.json", judge_summary)
    costs_path = write_json(output_root / "judge_costs.json", cost_summary)
    semantic_summary_path = _write_semantic_summary_csv(
        output_root / "semantic_business_summary.csv",
        judge_summary,
    )
    reasoning_path = output_root / "judge_reasoning.md"
    reasoning_path.write_text(
        _render_reasoning(judge_summary, judgments), encoding="utf-8"
    )

    return {
        "judgments": judgments_path,
        "summary": summary_path,
        "costs": costs_path,
        "semantic_summary": semantic_summary_path,
        "reasoning": reasoning_path,
    }


def _write_semantic_summary_csv(path: Path, summary: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    counts = summary.get("semantic_business_counts", {})
    verdict_counts = summary.get("verdict_counts", {})
    row = {
        "provider": summary.get("provider"),
        "model": summary.get("model"),
        "prompt_version": summary.get("prompt_version"),
        "judge_policy": summary.get("judge_policy"),
        "authoritative": summary.get("authoritative"),
        "total_predictions": summary.get("total_predictions"),
        "total_judged": summary.get("total_judged"),
        "semantic_correct": counts.get("correct", 0),
        "semantic_incorrect": counts.get("incorrect", 0),
        "semantic_unjudged": counts.get("unjudged", 0),
        "exact_sql_match": verdict_counts.get("exact_sql_match", 0),
        "invalid_sql": verdict_counts.get("invalid_sql", 0),
        "missing_sql": verdict_counts.get("missing_sql", 0),
        "requires_semantic_review": verdict_counts.get("requires_semantic_review", 0),
        "provider_error": verdict_counts.get("provider_error", 0),
        "provider_parse_error": verdict_counts.get("provider_parse_error", 0),
        "reasoning_tokens": summary.get("reasoning_tokens", 0),
        "reasoning_details_present": summary.get("reasoning_details_present", 0),
        "other_verdicts_json": json.dumps(
            {
                key: value
                for key, value in verdict_counts.items()
                if key
                not in {
                    "exact_sql_match",
                    "invalid_sql",
                    "missing_sql",
                    "requires_semantic_review",
                    "provider_error",
                    "provider_parse_error",
                }
            },
            ensure_ascii=False,
            sort_keys=True,
        ),
    }
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(row))
        writer.writeheader()
        writer.writerow(row)
    return path


def _render_reasoning(summary: dict[str, Any], judgments: list[dict[str, Any]]) -> str:
    lines = [
        "# Phase 16 Judge Report",
        "",
        f"Generated at: {summary['generated_at']}",
        "",
        "## Source",
        "",
        f"- artifact: `{summary['source_artifact']}`",
        f"- provider: `{summary['provider']}`",
        f"- model: `{summary['model']}`",
        f"- prompt_version: `{summary['prompt_version']}`",
        f"- judge_policy: `{summary.get('judge_policy')}`",
        f"- authoritative: `{summary['authoritative']}`",
        "",
        "## Anti-Fake Statement",
        "",
        summary["anti_fake_policy"],
        "",
        "## Summary",
        "",
        f"- total_predictions: `{summary['total_predictions']}`",
        f"- total_judged: `{summary['total_judged']}`",
        f"- verdict_counts: `{summary['verdict_counts']}`",
        f"- semantic_business_counts: `{summary['semantic_business_counts']}`",
        "",
        "## Judgment Rows",
        "",
        "| Case | Verdict | Semantic Correct | Reason |",
        "|---|---|---|---|",
    ]
    for row in judgments:
        reason = str(row.get("reason") or "").replace("|", "/")
        lines.append(
            f"| {row.get('case_id')} | {row.get('verdict')} | {row.get('semantic_business_correct')} | {reason} |"
        )
    lines.append("")
    return "\n".join(lines)
