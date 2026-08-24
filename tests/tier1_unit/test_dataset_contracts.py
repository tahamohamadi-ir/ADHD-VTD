from __future__ import annotations

import pytest

from src.evaluation.dataset_loader import (
    behavioral_example_from_case,
    load_behavioral_examples,
    load_positive_examples,
    positive_example_from_case,
    summarize_dataset_package,
    write_json,
)


def test_positive_example_contract_requires_sql():
    example = positive_example_from_case(
        {
            "id": "VTD-1",
            "question_fa": "تعداد دانشجوها چقدر است؟",
            "difficulty": "easy",
            "category": "count",
            "sql": "SELECT COUNT(*) AS n FROM student_depression",
            "expected_tables": ["student_depression"],
            "expected_columns": ["student_depression.student_depression_id"],
        }
    )

    assert example.id == "VTD-1"
    assert example.sql.startswith("SELECT")
    assert example.expected_tables == ["student_depression"]


def test_positive_example_contract_rejects_missing_sql():
    with pytest.raises(ValueError, match="missing gold SQL"):
        positive_example_from_case({"id": "VTD-2", "question_fa": "چند نفر؟"})


def test_behavioral_example_contract_keeps_non_sql_out_of_ex():
    example = behavioral_example_from_case(
        {
            "id": "VTD-EVAL-1",
            "evaluation_type": "ambiguous",
            "user_utterance_fa": "این را تحلیل کن",
            "should_generate_sql": False,
            "expected_action": "ask_clarification",
        }
    )

    assert example.should_generate_sql is False
    assert example.expected_action == "ask_clarification"


def test_contract_loaders_split_positive_and_behavioral(tmp_path):
    positive_path = tmp_path / "positive.json"
    behavior_path = tmp_path / "behavior.json"
    write_json(
        positive_path,
        {
            "positive_examples": [
                {
                    "id": "VTD-1",
                    "question_fa": "تعداد؟",
                    "sql": "SELECT COUNT(*) AS n FROM student_depression",
                }
            ]
        },
    )
    write_json(
        behavior_path,
        {
            "behavioral_examples": [
                {
                    "id": "VTD-EVAL-1",
                    "user_utterance_fa": "حذف کن",
                    "should_generate_sql": False,
                    "expected_action": "refuse_unsafe_sql",
                }
            ]
        },
    )

    assert load_positive_examples(positive_path)[0].id == "VTD-1"
    assert load_behavioral_examples(behavior_path)[0].expected_action == "refuse_unsafe_sql"


def test_dataset_package_summary_counts_sql_and_behavioral():
    summary = summarize_dataset_package(
        [
            {"id": "p1", "gold_sql": "SELECT 1", "difficulty": "easy"},
            {"id": "b1", "should_generate_sql": False, "expected_action": "ask_clarification"},
        ]
    )

    assert summary.total == 2
    assert summary.sql_positive == 1
    assert summary.behavioral == 1
