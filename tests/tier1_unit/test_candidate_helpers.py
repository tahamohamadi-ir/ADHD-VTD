from src.graph.nodes.candidate_helpers import (
    candidate_adoption_id,
    candidate_by_id,
    candidate_generation_prompt,
    candidate_is_viable,
    candidate_prompt_variant,
    candidate_runtime_score,
    can_generate_extra_candidates,
    first_candidate_id,
    validation_issues_as_dict,
)
from src.graph.state import VTDState
from src.sql_validation.validation_result import ValidationIssue


def _candidate(candidate_id: str, score: float, **updates):
    data = {
        "candidate_id": candidate_id,
        "sql": f"SELECT {score} AS score",
        "valid_sql": True,
        "execution_passed": True,
        "metadata": {"candidate_score": {"score": score}},
    }
    data.update(updates)
    return data


def test_candidate_lookup_and_viability_helpers():
    candidates = [_candidate("candidate_1", 0.2), _candidate("candidate_2", 0.7)]

    assert first_candidate_id(candidates) == "candidate_1"
    assert candidate_by_id(candidates, "candidate_2") == candidates[1]
    assert candidate_by_id(candidates, "missing") is None
    assert candidate_is_viable(candidates[0])
    assert not candidate_is_viable(_candidate("candidate_3", 0.9, valid_sql=False))
    assert not candidate_is_viable(_candidate("candidate_4", 0.9, execution_passed=False))
    assert not candidate_is_viable(_candidate("candidate_5", 0.9, sql=None))


def test_candidate_prompt_variant_and_suffix_are_deterministic():
    assert candidate_prompt_variant(0) == "primary"
    assert candidate_prompt_variant(2) == "variant_3_conservative_cte_or_alias"
    assert candidate_prompt_variant(99) == "variant_3_conservative_cte_or_alias"

    primary_prompt = candidate_generation_prompt("base prompt   ", "primary")
    variant_prompt = candidate_generation_prompt(
        "base prompt   ",
        "variant_2_independent_equivalent",
    )

    assert primary_prompt == "base prompt"
    assert variant_prompt.startswith("base prompt")
    assert "Candidate verifier variant 2" in variant_prompt


def test_candidate_adoption_requires_non_primary_score_improvement_and_select_action():
    candidates = [_candidate("candidate_1", 8.0), _candidate("candidate_2", 9.0)]

    assert (
        candidate_adoption_id(
            candidates,
            selected_candidate_id="candidate_2",
            adoption_enabled=True,
            consistency_passed=True,
            verifier_action="select",
            primary_id="candidate_1",
        )
        == "candidate_2"
    )
    assert (
        candidate_adoption_id(
            candidates,
            selected_candidate_id="candidate_2",
            adoption_enabled=True,
            consistency_passed=True,
            verifier_action="clarify",
            primary_id="candidate_1",
        )
        is None
    )
    assert (
        candidate_adoption_id(
            candidates,
            selected_candidate_id="candidate_1",
            adoption_enabled=True,
            consistency_passed=True,
            verifier_action="select",
            primary_id="candidate_1",
        )
        is None
    )


def test_candidate_runtime_score_handles_missing_or_malformed_scores():
    assert candidate_runtime_score(_candidate("candidate_1", 7.5)) == 7.5
    assert candidate_runtime_score({"metadata": {"candidate_score": {"score": "bad"}}}) == 0.0
    assert candidate_runtime_score({"metadata": {}}) == 0.0


def test_validation_issues_as_dict_strips_gold_or_reference_fields():
    issues = [
        {
            "code": "INVALID_SQL",
            "message": "bad",
            "gold_sql": "SELECT hidden FROM gold",
            "reference_answer": "hidden",
        },
        ValidationIssue("UNKNOWN_COLUMN", "Unknown column: x", location="x"),
    ]

    normalized = validation_issues_as_dict(issues)

    assert normalized[0] == {"code": "INVALID_SQL", "message": "bad"}
    assert "gold_sql" not in str(normalized)
    assert "reference_answer" not in str(normalized)
    assert normalized[1] == {
        "code": "UNKNOWN_COLUMN",
        "message": "Unknown column: x",
        "severity": "error",
        "location": "x",
    }


def test_can_generate_extra_candidates_only_before_repair_loop():
    assert can_generate_extra_candidates(VTDState(trace_id="t", raw_question="q"))
    assert not can_generate_extra_candidates(
        VTDState(trace_id="t", raw_question="q", retry_count=1)
    )
    assert not can_generate_extra_candidates(
        VTDState(
            trace_id="t",
            raw_question="q",
            validation_errors=[{"message": "previous invalid SQL"}],
        )
    )
    assert not can_generate_extra_candidates(
        VTDState(trace_id="t", raw_question="q", execution_error="failed")
    )
