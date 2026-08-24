"""Unit tests for PersianNormalizer."""

from __future__ import annotations

import pytest

from src.nlu.persian_normalizer import PersianNormalizer


@pytest.fixture
def normalizer():
    return PersianNormalizer()


class TestArabicToPersian:
    """Test Arabic → Persian character normalization."""

    def test_arabic_kaf_to_persian(self, normalizer):
        assert "ک" in normalizer.normalize_text("كلمه")

    def test_arabic_yeh_to_persian(self, normalizer):
        assert "ی" in normalizer.normalize_text("يک")

    def test_arabic_yeh_variant(self, normalizer):
        assert "ی" in normalizer.normalize_text("ى")

    def test_teh_marbuta(self, normalizer):
        assert "ه" in normalizer.normalize_text("ة")


class TestDigitNormalization:
    """Test Persian/Arabic digit → ASCII digit conversion."""

    def test_persian_digits(self, normalizer):
        result = normalizer.normalize_text("۱۲۳")
        assert "123" in result

    def test_arabic_digits(self, normalizer):
        result = normalizer.normalize_text("٤٥٦")
        assert "456" in result

    def test_mixed_digits(self, normalizer):
        result = normalizer.normalize_text("۱۲ و ٣٤")
        assert "12" in result
        assert "34" in result


class TestZWNJ:
    """Test Zero-Width Non-Joiner handling."""

    def test_zwnj_replaced_with_space(self, normalizer):
        result = normalizer.normalize_text("می\u200cخواهم")
        assert "\u200c" not in result

    def test_multiple_zwnj(self, normalizer):
        result = normalizer.normalize_text("این\u200cکه\u200cنیست")
        assert "\u200c" not in result


class TestTypoFixes:
    """Test common Persian typo corrections."""

    def test_afsoordegi_to_afsordegi(self, normalizer):
        result = normalizer.normalize_text("افسوردگی")
        assert "افسردگی" in result

    def test_ezterab_to_ezterab(self, normalizer):
        result = normalizer.normalize_text("اضتراب")
        assert "اضطراب" in result

    def test_social_media(self, normalizer):
        result = normalizer.normalize_text("سوشال مدیا")
        assert "شبکه اجتماعی" in result


class TestColloquialMapping:
    """Test colloquial/Finglish mapping integration."""

    def test_depression_english(self, normalizer):
        result = normalizer.normalize_text("depression rate")
        assert "افسردگی" in result

    def test_finglish_anxiety(self, normalizer):
        result = normalizer.normalize_text("ezterab")
        assert "اضطراب" in result

    def test_student_english(self, normalizer):
        result = normalizer.normalize_text("student ha")
        assert "دانشجوها" in result


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_string(self, normalizer):
        result = normalizer.normalize_text("")
        assert result == ""

    def test_none_handling(self, normalizer):
        result = normalizer.normalize_text(None)
        assert result == ""

    def test_pure_english(self, normalizer):
        result = normalizer.normalize_text("SELECT COUNT(*)")
        assert "SELECT" in result or "select" in result.lower()

    def test_preserves_result_object(self, normalizer):
        result = normalizer.normalize("تست")
        assert result.original == "تست"
        assert result.normalized is not None
