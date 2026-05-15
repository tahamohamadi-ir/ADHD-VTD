from __future__ import annotations

import pytest

from src.evaluation.dataset_loader import select_samples_per_level, summarize_cases


def test_select_samples_per_level_is_deterministic_by_difficulty():
    cases = [
        {"id": "m1", "difficulty": "medium"},
        {"id": "e1", "difficulty": "easy"},
        {"id": "m2", "difficulty": "medium"},
        {"id": "e2", "difficulty": "easy"},
        {"id": "h1", "difficulty": "hard"},
        {"id": "e3", "difficulty": "easy"},
    ]

    selected = select_samples_per_level(cases, 2)

    assert [case["id"] for case in selected] == ["e1", "e2", "h1", "m1", "m2"]
    assert summarize_cases(selected)["by_difficulty"] == {"easy": 2, "hard": 1, "medium": 2}


def test_select_samples_per_level_rejects_non_positive_count():
    with pytest.raises(ValueError, match="samples_per_level"):
        select_samples_per_level([{"id": "x", "difficulty": "easy"}], 0)
