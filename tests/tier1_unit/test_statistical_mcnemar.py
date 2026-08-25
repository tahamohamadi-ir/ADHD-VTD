from __future__ import annotations

from src.evaluation.statistical_tests import exact_mcnemar_test


def test_exact_mcnemar_equal_discordant_counts_yields_p_one():
    result = exact_mcnemar_test(5, 5)

    assert result.b == 5
    assert result.c == 5
    assert result.n == 10
    assert result.statistic == 0.1
    assert result.p_value == 1.0
    assert result.significant_at_0_05 is False


def test_exact_mcnemar_asymmetric_counts_match_binomial_tail():
    first = exact_mcnemar_test(9, 1)
    second = exact_mcnemar_test(1, 9)

    assert first.n == 10
    assert first.statistic == 4.9
    assert first.p_value == 0.021484
    assert first.significant_at_0_05 is True
    assert second.p_value == first.p_value
    assert (second.b, second.c) == (1, 9)


def test_exact_mcnemar_zero_discordant_pairs_is_degenerate():
    result = exact_mcnemar_test(0, 0)

    assert result.b == 0
    assert result.c == 0
    assert result.n == 0
    assert result.statistic == 0.0
    assert result.p_value == 1.0
    assert result.significant_at_0_05 is False


def test_exact_mcnemar_single_sided_extremes_cross_threshold():
    below = exact_mcnemar_test(0, 5)
    above = exact_mcnemar_test(0, 6)

    assert below.p_value == 0.0625
    assert below.significant_at_0_05 is False
    assert above.p_value == 0.03125
    assert above.significant_at_0_05 is True
    assert above.statistic == round(25 / 6, 6)


def test_exact_mcnemar_known_twelve_pair_case():
    result = exact_mcnemar_test(2, 10)

    assert result.n == 12
    assert result.statistic == round(49 / 12, 6)
    assert result.p_value == 0.038574
    assert result.significant_at_0_05 is True


def test_exact_mcnemar_as_dict_round_trips_fields():
    payload = exact_mcnemar_test(3, 7).as_dict()

    assert set(payload) == {
        "b",
        "c",
        "n",
        "statistic",
        "p_value",
        "significant_at_0_05",
    }
    assert payload["n"] == 10
    assert isinstance(payload["significant_at_0_05"], bool)
