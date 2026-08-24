"""Unit tests for ColloquialMapper."""

from __future__ import annotations

import pytest

from src.nlu.colloquial_mapper import ColloquialMapper


@pytest.fixture
def mapper():
    return ColloquialMapper()


class TestDepressionTerms:
    """Test depression-related colloquial/Finglish mapping."""

    def test_english_depression(self, mapper):
        result = mapper.normalize("depression rate")
        assert "افسردگی" in result.normalized

    def test_finglish_depreshon(self, mapper):
        result = mapper.normalize("دیپرشن")
        assert "افسردگی" in result.normalized

    def test_colloquial_afsordegi(self, mapper):
        result = mapper.normalize("افسوردگی")
        assert "افسردگی" in result.normalized

    def test_depressed(self, mapper):
        result = mapper.normalize("depressed students")
        assert "افسردگی" in result.normalized


class TestAnxietyTerms:
    """Test anxiety-related mapping."""

    def test_english_anxiety(self, mapper):
        result = mapper.normalize("anxiety level")
        assert "اضطراب" in result.normalized

    def test_finglish_ezterab(self, mapper):
        result = mapper.normalize("ezterab")
        assert "اضطراب" in result.normalized

    def test_typo_ezterab(self, mapper):
        result = mapper.normalize("اضتراب")
        assert "اضطراب" in result.normalized


class TestStudentTerms:
    """Test student-related mapping."""

    def test_students_english(self, mapper):
        result = mapper.normalize("students")
        assert "دانشجوها" in result.normalized

    def test_student_ha(self, mapper):
        result = mapper.normalize("student ha")
        assert "دانشجوها" in result.normalized


class TestCGPATerms:
    """Test CGPA/GPA mapping."""

    def test_cgpa(self, mapper):
        result = mapper.normalize("cgpa score")
        assert "cgpa" in result.normalized.lower()

    def test_gpa(self, mapper):
        result = mapper.normalize("gpa of students")
        assert "cgpa" in result.normalized.lower()


class TestMatchedTerms:
    """Test that matched terms are properly tracked."""

    def test_matched_dict_populated(self, mapper):
        result = mapper.normalize("depression rate among students")
        assert len(result.matched_terms) > 0

    def test_original_preserved(self, mapper):
        text = "depression rate"
        result = mapper.normalize(text)
        assert result.original == text
