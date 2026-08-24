from typing import Any


CANDIDATE_PROMPT_VARIANTS: tuple[str, ...] = (
    "primary",
    "variant_2_independent_equivalent",
    "variant_3_conservative_cte_or_alias",
)

CANDIDATE_PROMPT_SUFFIXES: dict[str, str] = {
    "variant_2_independent_equivalent": """

Candidate verifier variant 2:
Independently solve the same question for verifier comparison.
Prefer a different safe SQLite formulation only if it preserves the exact requested semantics.
Allowed differences include explicit aliases, equivalent aggregate expressions, or a simple CTE.
Do not add hidden WHERE filters, hidden GROUP BY dimensions, new joins, new tables, or SELECT *.
Return only the same JSON object schema as the original prompt.
""",
    "variant_3_conservative_cte_or_alias": """

Candidate verifier variant 3:
Produce a conservative alternative SQL candidate for verifier comparison.
Keep the same query shape, requested filters, grouping keys, ranking/time grain, and schema scope.
If no safe equivalent alternative exists, return the canonical SQL rather than changing semantics.
Do not use destructive SQL, comments, SELECT *, or non-SQLite syntax.
Return only the same JSON object schema as the original prompt.
""",
}

_VALIDATION_ISSUE_KEYS = ("code", "type", "message", "severity", "location")


def first_candidate_id(candidates: list[dict[str, Any]]) -> str | None:
    if not candidates:
        return None
    return str(candidates[0].get("candidate_id"))


def candidate_by_id(
    candidates: list[dict[str, Any]], candidate_id: str | None
) -> dict[str, Any] | None:
    for candidate in candidates:
        if str(candidate.get("candidate_id")) == str(candidate_id):
            return candidate
    return None


def candidate_is_viable(candidate: dict[str, Any]) -> bool:
    return (
        bool(candidate.get("sql"))
        and candidate.get("valid_sql") is not False
        and candidate.get("execution_passed") is not False
    )


def candidate_prompt_variant(
    index: int,
    *,
    variants: tuple[str, ...] = CANDIDATE_PROMPT_VARIANTS,
) -> str:
    if index < len(variants):
        return variants[index]
    return variants[-1]


def candidate_generation_prompt(
    base_prompt: str | None,
    prompt_variant: str,
    *,
    prompt_suffixes: dict[str, str] = CANDIDATE_PROMPT_SUFFIXES,
) -> str:
    prompt = (base_prompt or "").rstrip()
    suffix = prompt_suffixes.get(prompt_variant)
    if not suffix:
        return prompt
    return f"{prompt}{suffix.rstrip()}"


def candidate_is_adoption_improvement(
    selected: dict[str, Any],
    primary: dict[str, Any],
    *,
    primary_id: str,
) -> bool:
    if str(selected.get("candidate_id")) == str(primary_id):
        return False
    return candidate_runtime_score(selected) > candidate_runtime_score(primary)


def candidate_runtime_score(candidate: dict[str, Any]) -> float:
    metadata = candidate.get("metadata") if isinstance(candidate.get("metadata"), dict) else {}
    score = (
        metadata.get("candidate_score") if isinstance(metadata.get("candidate_score"), dict) else {}
    )
    try:
        return float(score.get("score"))
    except (TypeError, ValueError):
        return 0.0


def candidate_adoption_id(
    candidates: list[dict[str, Any]],
    *,
    selected_candidate_id: str | None,
    adoption_enabled: bool,
    consistency_passed: bool,
    verifier_action: str | None,
    primary_id: str | None = None,
) -> str | None:
    primary = candidates[0] if candidates else {}
    resolved_primary_id = primary_id or str(primary.get("candidate_id") or "candidate_1")
    selected = candidate_by_id(candidates, selected_candidate_id)
    if (
        adoption_enabled
        and consistency_passed
        and (verifier_action is None or verifier_action == "select")
        and selected is not None
        and candidate_is_viable(selected)
        and candidate_is_adoption_improvement(
            selected,
            primary,
            primary_id=resolved_primary_id,
        )
    ):
        return str(selected_candidate_id)
    return None


def validation_issues_as_dict(issues: list[Any]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for issue in issues:
        if isinstance(issue, dict):
            normalized.append({key: issue[key] for key in _VALIDATION_ISSUE_KEYS if key in issue})
            continue
        normalized.append(
            {
                "code": str(getattr(issue, "code", "VALIDATION_ERROR")),
                "message": str(getattr(issue, "message", issue)),
                "severity": str(getattr(issue, "severity", "error")),
                "location": getattr(issue, "location", None),
            }
        )
    return normalized


def can_generate_extra_candidates(state: Any) -> bool:
    """Keep extra generation off the repair loop until A/B evidence improves."""

    if state.retry_count > 0:
        return False
    if state.validation_errors or state.execution_error:
        return False
    return True
