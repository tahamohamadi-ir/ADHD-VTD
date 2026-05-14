"""Unit tests for NumberNormalizer."""
from __future__ import annotations

import pytest

from src.nlu.number_normalizer import NumberNormalizer


@pytest.fixture
def normalizer():
    return NumberNormalizer()


class TestDigitConversion:
    """Test Persian/Arabic digit → ASCII conversion."""

    def test_persian_digits(self, normalizer):
        assert normalizer.normalize_digits("۱۲۳") == "123"

    def test_arabic_digits(self, normalizer):
        assert normalizer.normalize_digits("٤٥٦") == "456"

    def test_mixed(self, normalizer):
        result = normalizer.normalize_digits("۱۲ abc ٣٤")
        assert "12" in result
        assert "34" in result

    def test_empty(self, normalizer):
        assert normalizer.normalize_digits("") == ""

    def test_no_digits(self, normalizer):
        assert normalizer.normalize_digits("hello") == "hello"


class TestWordToNumber:
    """Test Persian number words → digits conversion."""

    def test_yek(self, normalizer):
        result = normalizer.normalize_number_words("یک")
        assert "1" in result

    def test_do(self, normalizer):
        result = normalizer.normalize_number_words("دو")
        assert "2" in result

    def test_dah(self, normalizer):
        result = normalizer.normalize_number_words("ده")
        assert "10" in result

    def test_bist(self, normalizer):
        result = normalizer.normalize_number_words("بیست")
        assert "20" in result

    def test_sad(self, normalizer):
        result = normalizer.normalize_number_words("صد")
        assert "100" in result

    def test_in_sentence(self, normalizer):
        result = normalizer.normalize_number_words("پنج دانشجو")
        assert "5" in result


class TestExtractNumbers:
    """Test numeric value extraction."""

    def test_integer(self, normalizer):
        assert 123 in normalizer.extract_numbers("عدد 123 است")

    def test_float(self, normalizer):
        result = normalizer.extract_numbers("نمره 3.5 است")
        assert any(abs(v - 3.5) < 0.001 for v in result)

    def test_persian_digits(self, normalizer):
        assert 123 in normalizer.extract_numbers("۱۲۳")

    def test_no_numbers(self, normalizer):
        assert normalizer.extract_numbers("بدون عدد") == []

    def test_multiple_numbers(self, normalizer):
        result = normalizer.extract_numbers("بین 10 تا 20")
        assert 10 in result
        assert 20 in result


class TestFullNormalization:
    """Test the complete normalize() pipeline."""

    def test_result_structure(self, normalizer):
        result = normalizer.normalize("۱۲۳ و پنج")
        assert result.original == "۱۲۳ و پنج"
        assert "123" in result.normalized
        assert "5" in result.normalized
        assert len(result.extracted_numbers) >= 2
