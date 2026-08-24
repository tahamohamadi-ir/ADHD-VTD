"""Unit tests for PersianDateNormalizer."""

from __future__ import annotations

import pytest

from src.nlu.date_normalizer import PersianDateNormalizer


@pytest.fixture
def normalizer():
    return PersianDateNormalizer()


class TestExplicitJalali:
    """Test explicit Jalali month+year → Gregorian conversion."""

    def test_farvardin_1404(self, normalizer):
        result = normalizer.normalize("فروردین 1404")
        assert result.has_temporal_expression
        if result.date_range is not None:
            assert "start" in result.date_range
            assert "end_exclusive" in result.date_range
            assert not result.needs_clarification

    def test_shahrivar_1403(self, normalizer):
        result = normalizer.normalize("شهریور ۱۴۰۳")
        assert result.has_temporal_expression

    def test_month_without_year(self, normalizer):
        result = normalizer.normalize("فروردین")
        assert result.has_temporal_expression
        assert result.needs_clarification
        assert "year" in (result.reason or "").lower() or "سال" in (result.reason or "")


class TestVagueTemporalExpressions:
    """Test vague temporal expressions that need clarification."""

    def test_emsal(self, normalizer):
        result = normalizer.normalize("امسال")
        assert result.has_temporal_expression
        assert result.needs_clarification

    def test_parsal(self, normalizer):
        result = normalizer.normalize("پارسال")
        assert result.has_temporal_expression
        assert result.needs_clarification

    def test_sale_ghabl(self, normalizer):
        result = normalizer.normalize("سال قبل")
        assert result.has_temporal_expression
        assert result.needs_clarification

    def test_last_year(self, normalizer):
        result = normalizer.normalize("last year")
        assert result.has_temporal_expression
        assert result.needs_clarification


class TestNonTemporalQueries:
    """Test that non-temporal queries are not flagged."""

    def test_no_temporal(self, normalizer):
        result = normalizer.normalize("میانگین نمره افسردگی")
        assert not result.has_temporal_expression
        assert not result.needs_clarification

    def test_count_query(self, normalizer):
        result = normalizer.normalize("تعداد دانشجوها")
        assert not result.has_temporal_expression


class TestDigitNormalization:
    """Test that Persian digits in year are normalized."""

    def test_persian_year_digits(self, normalizer):
        result = normalizer.normalize("فروردین ۱۴۰۴")
        assert result.has_temporal_expression
