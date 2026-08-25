"""Tests for the near-miss partial-credit wiring in the benchmark CLI."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from scripts.run_benchmark import _near_miss_partial_credit  # noqa: E402


def _executor(gen_rows, gold_rows, gen_ok=True, gold_ok=True):
    def execute(sql: str):
        if "BROKEN" in sql:
            return SimpleNamespace(ok=False, rows=[], error="boom")
        if "GOLD" in sql:
            return SimpleNamespace(ok=gold_ok, rows=gold_rows, error=None)
        return SimpleNamespace(ok=gen_ok, rows=gen_rows, error=None)

    class E:
        execute_readonly = staticmethod(execute)

    return E()


class TestNearMissPartialCredit:
    def test_match_short_circuits_to_one(self) -> None:
        assert (
            _near_miss_partial_credit(None, "s", "g", {"match": True}) == 1.0
        )

    def test_none_when_generation_failed(self) -> None:
        cmp = {"match": False, "generated_ok": False, "gold_ok": True}
        assert _near_miss_partial_credit(None, "SELECT BROKEN", "SELECT GOLD", cmp) is None

    def test_near_miss_scored(self) -> None:
        cmp = {"match": False, "generated_ok": True, "gold_ok": True}
        score = _near_miss_partial_credit(
            _executor([("a", 1)], [("a", 1), ("b", 2)]),
            "SELECT a FROM t",
            "SELECT GOLD",
            cmp,
        )
        assert score is not None
        assert 0.0 < score < 1.0

    def test_execution_error_returns_none(self) -> None:
        cmp = {"match": False, "generated_ok": True, "gold_ok": True}
        score = _near_miss_partial_credit(
            _executor([("a", 1)], [("a", 1)], gold_ok=False),
            "SELECT a FROM t",
            "SELECT GOLD",
            cmp,
        )
        assert score is None

    def test_exact_same_rows_score_one(self) -> None:
        cmp = {"match": False, "generated_ok": True, "gold_ok": True}
        score = _near_miss_partial_credit(
            _executor([("a", 1), ("b", 2)], [("a", 1), ("b", 2)]),
            "SELECT a FROM t",
            "SELECT GOLD",
            cmp,
        )
        assert score == 1.0
