from __future__ import annotations

import pytest

from src.sql_validation.surgeon import (
    BalancedQuoteFixStrategy,
    StripCodeFenceStrategy,
    SurgeonOutcome,
    TrailingSemicolonStrategy,
    apply_surgeon,
)


def test_outcome_is_frozen_dataclass_with_aligned_sequences():
    outcome = apply_surgeon("SELECT 1;")
    assert isinstance(outcome, SurgeonOutcome)
    assert len(outcome.applied) == len(outcome.confidences)
    with pytest.raises(Exception):
        outcome.original = "mutated"


def test_strip_code_fence_positive():
    outcome = apply_surgeon("```sql\nSELECT id FROM students\n```")
    assert outcome.repaired == "SELECT id FROM students"
    assert outcome.applied == ("strip_code_fence",)
    assert outcome.confidences == (StripCodeFenceStrategy.confidence,)


def test_strip_code_fence_negative_plain_sql_untouched():
    outcome = apply_surgeon("SELECT id FROM students")
    assert outcome.repaired == outcome.original
    assert outcome.applied == ()


def test_strip_code_fence_negative_unterminated_fence_not_touched():
    sql = "```sql\nSELECT id FROM students"
    outcome = apply_surgeon(sql)
    assert outcome.repaired == sql
    assert outcome.applied == ()


def test_trailing_semicolon_positive_strips_semicolon_and_whitespace():
    outcome = apply_surgeon("SELECT 1  ;\n\t ")
    assert outcome.repaired == "SELECT 1"
    assert outcome.applied == ("trailing_semicolon",)
    assert outcome.confidences == (TrailingSemicolonStrategy.confidence,)


def test_trailing_semicolon_negative_no_semicolon():
    outcome = apply_surgeon("SELECT 1")
    assert outcome.repaired == "SELECT 1"
    assert outcome.applied == ()


def test_trailing_semicolon_keeps_semicolon_inside_string_literal():
    sql = "SELECT ';' AS marker"
    outcome = apply_surgeon(sql)
    assert outcome.repaired == sql
    assert outcome.applied == ()


def test_balanced_quote_fix_positive_appends_missing_closing_quote():
    broken = "SELECT name FROM users WHERE name = 'ali"
    outcome = apply_surgeon(broken)
    assert outcome.repaired == "SELECT name FROM users WHERE name = 'ali'"
    assert outcome.applied == ("balanced_quote_fix",)
    assert outcome.confidences == (BalancedQuoteFixStrategy.confidence,)


def test_balanced_quote_fix_negative_even_quotes_and_broken_parse():
    sql = "SELECT FROM WHERE ORDER"
    strategy = BalancedQuoteFixStrategy()
    assert strategy.apply(sql) is None
    outcome = apply_surgeon(sql)
    assert outcome.repaired == sql
    assert outcome.applied == ()


def test_balanced_quote_fix_negative_odd_quote_but_already_parses():
    sql = "SELECT 1 -- it's fine"
    strategy = BalancedQuoteFixStrategy()
    assert strategy.apply(sql) is None
    outcome = apply_surgeon(sql)
    assert outcome.repaired == sql
    assert outcome.applied == ()


def test_multi_round_repairs_fence_then_semicolon():
    outcome = apply_surgeon("```sql\nSELECT id FROM students;\n```")
    assert outcome.repaired == "SELECT id FROM students"
    assert outcome.applied == ("strip_code_fence", "trailing_semicolon")
    assert outcome.confidences == (
        StripCodeFenceStrategy.confidence,
        TrailingSemicolonStrategy.confidence,
    )


def test_max_rounds_caps_applied_strategies():
    outcome = apply_surgeon("```sql\nSELECT id FROM students;\n```", max_rounds=1)
    assert outcome.applied == ("strip_code_fence",)
    assert outcome.repaired.endswith(";")


def test_max_rounds_zero_returns_original():
    outcome = apply_surgeon("SELECT 1;", max_rounds=0)
    assert outcome.repaired == outcome.original
    assert outcome.applied == ()
    assert outcome.confidences == ()


@pytest.mark.parametrize(
    "garbage",
    [
        "",
        "\x00\x01\x02",
        "((((( ",
        "```\n```sql",
        "SELECT 'unterminated AND ;;;   ",
        "LIMIT 999999",
    ],
)
def test_hard_garbage_returns_original_without_raising(garbage: str):
    outcome = apply_surgeon(garbage)
    assert isinstance(outcome, SurgeonOutcome)
    assert outcome.original == garbage
    assert outcome.repaired in {garbage, garbage.rstrip() + "'"}


@pytest.mark.parametrize(
    "lenient",
    [
        "```sql\nGARBAGE NOT SQL\n```",
        "\u0633\u0644\u0627\u0645 \u062e\u0627\u0646\u0648\u0645 ;;;",
    ],
)
def test_lenient_parseable_repair_is_accepted_and_idempotent(lenient: str):
    outcome = apply_surgeon(lenient)
    assert outcome.repaired != lenient
    assert len(outcome.applied) >= 1
    reapplied = apply_surgeon(outcome.repaired)
    assert reapplied.repaired == outcome.repaired
    assert reapplied.applied == ()


def test_limit_clamp_strategy_is_intentionally_absent():
    sql = "SELECT score FROM exams LIMIT 5000"
    outcome = apply_surgeon(sql)
    assert outcome.repaired == sql
    assert "limit_clamp" not in outcome.applied


@pytest.mark.parametrize(
    "sql",
    [
        "```sql\nSELECT id FROM students\n```",
        "SELECT 1 ;",
        "SELECT name FROM users WHERE name = 'ali",
        "```sql\nSELECT id FROM students;\n```",
    ],
)
def test_idempotency_reapplying_repaired_sql_changes_nothing(sql: str):
    first = apply_surgeon(sql)
    second = apply_surgeon(first.repaired)
    assert second.repaired == first.repaired
    assert second.applied == ()
    assert second.confidences == ()
