from __future__ import annotations

import pytest

from src.evaluation.metrics import partial_credit_semantic_score


def test_identical_rows_score_one():
    expected = [(1, "ali"), (2, "sara")]
    actual = [(1, "ali"), (2, "sara")]

    assert partial_credit_semantic_score(expected, actual) == 1.0


def test_both_empty_scores_one_and_single_sided_empty_scores_zero():
    assert partial_credit_semantic_score([], []) == 1.0
    assert partial_credit_semantic_score([(1,)], []) == 0.0
    assert partial_credit_semantic_score([], [(1,)]) == 0.0


def test_half_rows_recovered_score_zero_point_six():
    expected = [(1, "a"), (2, "b")]
    actual = [(1, "a")]

    score = partial_credit_semantic_score(expected, actual)

    assert score == pytest.approx(0.60)


def test_disjoint_values_with_matching_shape_score_zero_point_five():
    expected = [(1,)]
    actual = [(2,)]

    assert partial_credit_semantic_score(expected, actual) == pytest.approx(0.50)


def test_column_count_mismatch_penalizes_only_column_component():
    expected = [(1, 2)]
    actual = [(1, 2, 3)]

    score = partial_credit_semantic_score(expected, actual)

    assert score == pytest.approx(0.30 + 0.50 * (2 / 3))


def test_extra_actual_rows_are_capped_not_penalized():
    expected = [(7,)]
    actual = [(7,), (7,), (7,)]

    assert partial_credit_semantic_score(expected, actual) == 1.0


def test_float_cells_match_within_four_decimals():
    expected = [(1.00000001, "x")]
    actual = [(1.0, "x")]

    assert partial_credit_semantic_score(expected, actual) == 1.0


def test_cell_normalization_strips_and_lowercases_strings():
    expected = [(" Ali ", 5)]
    actual = [("ali", 5)]

    assert partial_credit_semantic_score(expected, actual) == 1.0
