from __future__ import annotations

from src.output.explanation_builder import build_explanation


def test_non_generate_sql_action_returns_none():
    assert build_explanation({"actual_action": "refuse_unsafe_sql"}) is None


def test_missing_sql_returns_none():
    assert build_explanation({"actual_action": "generate_sql"}) is None


def test_explanation_contains_sql_block():
    result = build_explanation(
        {
            "actual_action": "generate_sql",
            "generated_sql": "SELECT COUNT(*) FROM t",
        }
    )

    assert result is not None
    assert "```sql" in result
    assert "SELECT COUNT(*) FROM t" in result


def test_explanation_lists_assumptions_from_parsed_payload():
    result = build_explanation(
        {
            "actual_action": "generate_sql",
            "generated_sql": "SELECT 1",
            "parsed_payload": {"assumptions": ["فرض یک", "فرض دو"]},
        }
    )

    assert result is not None
    assert "- فرض یک" in result
    assert "- فرض دو" in result
