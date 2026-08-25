"""Tests for EGIR wiring inside the check_consistency graph node."""

from __future__ import annotations

from src.graph.nodes.check_consistency_node import check_consistency
from src.graph.state import VTDState


def _state(**overrides) -> VTDState:
    defaults = {
        "trace_id": "t-egir",
        "raw_question": "تعداد دانشجویان به تفکیک جنسیت",
        "generated_sql": "SELECT COUNT(*) FROM student_depression",
    }
    defaults.update(overrides)
    return VTDState(**defaults)


class TestEgirWiring:
    def test_egir_report_attached_and_issue_found(self) -> None:
        payload = check_consistency(_state())
        egir = payload["egir_report"]
        assert egir is not None
        assert egir["ok"] is False
        codes = {i["code"] for i in egir["issues"]}
        assert "MISSING_GROUP_BY" in codes
        assert all(i["severity"] == "warning" for i in egir["issues"])

    def test_merged_into_candidate_report(self) -> None:
        report = check_consistency(_state())["candidate_consistency_report"]
        assert isinstance(report, dict)
        assert report.get("egir_ok") is False
        assert any(i["code"] == "MISSING_GROUP_BY" for i in report.get("egir_issues", []))

    def test_clean_sql_passes_egir(self) -> None:
        payload = check_consistency(
            _state(
                generated_sql=(
                    "SELECT gender, COUNT(*) FROM student_depression GROUP BY gender"
                )
            )
        )
        assert payload["egir_report"]["ok"] is True

    def test_no_question_no_crash(self) -> None:
        payload = check_consistency(_state(raw_question="", normalized_question=None))
        assert payload["candidate_consistency_report"] is None
        assert payload.get("egir_report") is None

    def test_row_count_from_execution_result(self) -> None:
        payload = check_consistency(
            _state(execution_result=[{"a": 1}, {"a": 2}])
        )
        # split intent without group by still flagged regardless of rows; ensure no crash
        assert "egir_report" in payload
