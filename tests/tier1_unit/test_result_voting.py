"""Tests for fuzzy result-cluster voting (idea #7, flag-gated)."""

from __future__ import annotations

import pytest

from src.config import features
from src.evaluation.candidate_consistency import analyze_candidate_consistency
from src.evaluation.result_voting import (
    results_equivalent,
    select_candidate_by_fuzzy_clusters,
)


class TestResultsEquivalent:
    def test_identical_rows(self) -> None:
        assert results_equivalent([("a", 1)], [("a", 1)]) is True

    def test_row_count_ratio_guard(self) -> None:
        rows_a = [(i,) for i in range(10)]
        rows_b = [(i,) for i in range(4)]
        assert results_equivalent(rows_a, rows_b) is False

    def test_within_tolerance_and_overlap(self) -> None:
        rows_a = [(i,) for i in range(10)]
        rows_b = [(i,) for i in range(9)]
        assert results_equivalent(rows_a, rows_b) is True

    def test_value_mismatch_below_jaccard(self) -> None:
        rows_a = [(i,) for i in range(10)]
        rows_b = [(100 + i,) for i in range(10)]
        assert results_equivalent(rows_a, rows_b) is False

    def test_float_rounding_normalized(self) -> None:
        assert results_equivalent([("x", 0.33331)], [("x", 0.33332)]) is True

    def test_both_empty(self) -> None:
        assert results_equivalent([], []) is True


class TestFuzzyClusterVote:
    def test_largest_cluster_wins(self) -> None:
        pick = select_candidate_by_fuzzy_clusters(
            [
                ("c1", [(1,), (2,)]),
                ("c2", [(1,), (2,)]),
                ("c3", [(99,)]),
            ]
        )
        assert pick == "c1"

    def test_empty_input(self) -> None:
        assert select_candidate_by_fuzzy_clusters([]) is None

    def test_all_disjoint_returns_first_seed(self) -> None:
        pick = select_candidate_by_fuzzy_clusters(
            [("c1", [(1,)]), ("c2", [(2,)]), ("c3", [(3,)])]
        )
        assert pick == "c1"


class TestFlagGatedConsistencyFallback:
    def _candidates(self) -> list[dict]:
        return [
            {
                "candidate_id": "c1",
                "sql": "SELECT a FROM t",
                "valid_sql": True,
                "execution_passed": True,
                "result_hash": "h1",
                "execution_rows": [("x",)],
            },
            {
                "candidate_id": "c2",
                "sql": "SELECT b FROM t",
                "valid_sql": True,
                "execution_passed": True,
                "result_hash": "h2",
                "execution_rows": [("y",)],
            },
            {
                "candidate_id": "c3",
                "sql": "SELECT c FROM t",
                "valid_sql": True,
                "execution_passed": True,
                "result_hash": "h3",
                "execution_rows": [("x",), ("z",)],
            },
        ]

    def test_flag_off_keeps_legacy_first_candidate(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(features, "ENABLE_RESULT_HASH_FUZZY_VOTING", False)
        report = analyze_candidate_consistency(self._candidates())
        assert report.selected_candidate_id == "c1"

    def test_flag_on_clusters_equivalent_results(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(features, "ENABLE_RESULT_HASH_FUZZY_VOTING", True)
        candidates = self._candidates()
        candidates[2]["execution_rows"] = [("x",)]
        report = analyze_candidate_consistency(candidates)
        assert report.selected_candidate_id == "c1"

    def test_rows_loaded_from_record(self) -> None:
        from src.evaluation.candidate_consistency import SqlCandidate

        cand = SqlCandidate.from_record(
            {"candidate_id": "c9", "sql": "SELECT 1", "execution_rows": [{"a": 1}]}, 0
        )
        assert cand.rows == [{"a": 1}]
