"""Tests for the deterministic EGIR intent-vs-shape critic."""

from __future__ import annotations

from src.sql_validation.egir import (
    check_intent_result_alignment,
    detect_intents,
)


class TestIntentDetection:
    def test_aggregate_detected(self) -> None:
        assert "aggregate" in detect_intents("میانگین سن دانشجویان چقدر است؟")

    def test_split_and_aggregate(self) -> None:
        intents = detect_intents("میانگین فشار تحصیلی به تفکیک جنسیت")
        assert "aggregate" in intents
        assert "split_by_group" in intents

    def test_trend(self) -> None:
        assert "trend_over_time" in detect_intents("روند اضطراب مالی طی زمان")

    def test_list(self) -> None:
        assert "raw_list" in detect_intents("لیست دانشجویان افسرده")

    def test_empty_question(self) -> None:
        assert detect_intents("") == ()


class TestAlignmentChecks:
    def test_missing_group_by_flagged(self) -> None:
        report = check_intent_result_alignment(
            "تعداد دانشجویان به تفکیک جنسیت",
            "SELECT COUNT(*) FROM student_depression",
        )
        assert not report.ok
        codes = {i.code for i in report.issues}
        assert "MISSING_GROUP_BY" in codes

    def test_split_with_group_by_passes(self) -> None:
        report = check_intent_result_alignment(
            "تعداد دانشجویان به تفکیک جنسیت",
            "SELECT gender, COUNT(*) FROM student_depression GROUP BY gender",
        )
        assert report.ok

    def test_trend_without_temporal_flagged(self) -> None:
        report = check_intent_result_alignment(
            "روند میانگین فشار تحصیلی",
            "SELECT AVG(academic_pressure) FROM student_depression",
        )
        assert not report.ok
        assert any(i.code == "TREND_WITHOUT_TEMPORAL_COLUMN" for i in report.issues)

    def test_list_answered_by_count_flagged(self) -> None:
        report = check_intent_result_alignment(
            "لیست دانشجویان با افسردگی",
            "SELECT COUNT(*) FROM student_depression WHERE depression_flag = 1",
        )
        assert not report.ok
        assert any(i.code == "LIST_REQUEST_ANSWERED_BY_COUNT" for i in report.issues)

    def test_unbounded_list_flagged_when_no_rowcount(self) -> None:
        report = check_intent_result_alignment(
            "لیست دانشجویان شهر تهران",
            "SELECT name FROM students WHERE city = 'تهران'",
            row_count=None,
        )
        assert any(i.code == "UNBOUNDED_LIST_QUERY" for i in report.issues)
        bounded = check_intent_result_alignment(
            "لیست دانشجویان شهر تهران",
            "SELECT name FROM students WHERE city = 'تهران' LIMIT 100",
            row_count=None,
        )
        assert all(i.code != "UNBOUNDED_LIST_QUERY" for i in bounded.issues)

    def test_neutral_sql_no_intents_ok(self) -> None:
        report = check_intent_result_alignment("سلام", "SELECT 1")
        assert report.ok
        assert report.matched_intents == ()

    def test_feedback_is_persian(self) -> None:
        report = check_intent_result_alignment(
            "تعداد به تفکیک جنسیت",
            "SELECT COUNT(*) FROM student_depression",
        )
        assert report.issues and all(i.feedback_fa for i in report.issues)
