from __future__ import annotations

from src.evaluation.action_normalizer import (
    actions_match,
    normalize_actual_action,
    normalize_expected_action,
    should_abstain_for_action,
)


def test_behavioral_refusal_aliases_normalize_to_unsafe_refusal():
    assert normalize_expected_action("refuse_privacy") == "refuse_unsafe_sql"
    assert normalize_expected_action("refuse_privacy_safety") == "refuse_unsafe_sql"
    assert normalize_expected_action("refuse_data_fabrication") == "refuse_unsafe_sql"
    assert normalize_expected_action("refuse_external_unverified_data") == "refuse_unsafe_sql"
    assert normalize_expected_action("safety_refusal") == "refuse_unsafe_sql"
    assert actions_match("refuse_privacy", "refuse_unsafe_sql")


def test_schema_gap_refusal_can_be_handled_by_clarification():
    assert normalize_expected_action("refuse_hallucination") == "refuse_schema_gap"
    assert actions_match("refuse_hallucination", "ask_clarification")
    assert actions_match("refuse_hallucination", "refuse_unsafe_sql")


def test_format_answer_counts_as_sql_when_sql_was_generated():
    assert normalize_actual_action("format_answer", generated_sql="SELECT 1") == "generate_sql"
    assert actions_match("generate_sql", "format_answer", generated_sql="SELECT 1")


def test_should_abstain_uses_normalized_behavioral_actions():
    assert should_abstain_for_action("refuse_privacy", should_generate_sql=False)
    assert not should_abstain_for_action("generate_sql", should_generate_sql=True)
