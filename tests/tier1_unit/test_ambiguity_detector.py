"""Unit tests for AmbiguityDetector."""

from __future__ import annotations

import pytest

from src.nlu.ambiguity_detector import AmbiguityDetector


@pytest.fixture
def detector():
    return AmbiguityDetector()


class TestGenericRequests:
    """Test detection of generic/vague requests."""

    def test_generic_stats(self, detector):
        result = detector.detect("یه آمار کلی بده")
        assert result.is_ambiguous

    def test_dashboard_request(self, detector):
        result = detector.detect("داشبورد بساز")
        assert result.is_ambiguous

    def test_summary_request(self, detector):
        result = detector.detect("خلاصه بده")
        assert result.is_ambiguous


class TestRankingWithoutMetric:
    """Test detection of ranking requests without ranking metric."""

    def test_best_without_metric(self, detector):
        result = detector.detect("بهترین ها رو نشون بده")
        assert result.is_ambiguous
        assert any("ranking" in r.lower() or "رتبه" in r for r in result.reasons)

    def test_worst_without_metric(self, detector):
        result = detector.detect("بدترین ها کدومن")
        assert result.is_ambiguous

    def test_top_without_metric(self, detector):
        result = detector.detect("top 10 رو بده")
        assert result.is_ambiguous

    def test_ranking_with_metric_ok(self, detector):
        """Ranking WITH a metric should NOT be ambiguous."""
        result = detector.detect("بالاترین نمره افسردگی")
        assert not result.is_ambiguous


class TestChartWithoutMeasure:
    """Test detection of chart requests without measure/dimension."""

    def test_chart_without_anything(self, detector):
        result = detector.detect("نمودار بساز")
        assert result.is_ambiguous
        assert any("chart" in r.lower() or "نمودار" in r for r in result.reasons)

    def test_chart_with_metric_ok(self, detector):
        """Chart with metric should not be ambiguous."""
        result = detector.detect("نمودار افسردگی بر اساس جنسیت")
        assert not result.is_ambiguous


class TestShortRequests:
    """Test detection of very short requests."""

    def test_two_word(self, detector):
        result = detector.detect("وضعیت چطوره")
        assert result.is_ambiguous

    def test_single_word(self, detector):
        result = detector.detect("آمار")
        assert result.is_ambiguous


class TestClearRequests:
    """Test that clear, well-formed requests are NOT ambiguous."""

    def test_count_with_metric(self, detector):
        result = detector.detect("تعداد دانشجوهایی که افسردگی دارند")
        assert not result.is_ambiguous

    def test_average_score(self, detector):
        result = detector.detect("میانگین نمره اضطراب دانشجوها")
        assert not result.is_ambiguous

    def test_dashboard_with_domain_metric_is_not_ambiguous(self, detector):
        question = (
            "\u062f\u0627\u0634\u0628\u0648\u0631\u062f "
            "\u062a\u063a\u06cc\u06cc\u0631 \u062c\u0647\u0627\u0646\u06cc eating_disorder: "
            "\u0645\u06cc\u0627\u0646\u06af\u06cc\u0646\u060c \u0635\u062f\u06a9\u200c\u0647\u0627 "
            "\u0648 \u0628\u06cc\u0634\u062a\u0631\u06cc\u0646 \u062a\u063a\u06cc\u06cc\u0631 "
            "\u06a9\u0634\u0648\u0631\u0647\u0627 \u0631\u0627 \u0628\u062f\u0647."
        )
        result = detector.detect(question)
        assert not result.is_ambiguous


class TestClarificationQuestion:
    """Test that clarification questions are generated."""

    def test_has_clarification_when_ambiguous(self, detector):
        result = detector.detect("یه آمار کلی بده")
        assert result.is_ambiguous
        assert result.clarification_question is not None
        assert len(result.clarification_question) > 10

    def test_no_clarification_when_clear(self, detector):
        result = detector.detect("تعداد دانشجوهایی که افسردگی دارند")
        assert result.clarification_question is None
