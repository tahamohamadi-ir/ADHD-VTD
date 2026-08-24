"""Unit tests for SchemaLinker."""

from __future__ import annotations
import pytest
from src.schema.schema_linker import SchemaLinker


@pytest.fixture
def linker():
    return SchemaLinker()


class TestDepressionLinking:
    def test_afsordegi(self, linker):
        r = linker.link("افسردگی دانشجوها")
        assert any("depression" in c for c in r.columns)

    def test_english(self, linker):
        r = linker.link("depression among students")
        assert any("depression" in c for c in r.columns)


class TestGenderLinking:
    def test_zan(self, linker):
        r = linker.link("دانشجوهای زن")
        assert any("gender" in c for c in r.columns)


class TestCGPA:
    def test_moadel(self, linker):
        r = linker.link("معدل دانشجوها")
        assert any("cgpa" in c for c in r.columns)


class TestSchemaLinkerPhase18Aliases:
    def test_student_depression_dataset_context_prefers_student_table(self, linker):
        r = linker.link(
            "\u0645\u06cc\u0627\u0646\u06af\u06cc\u0646 CGPA \u062f\u0627\u0646\u0634\u062c\u0648\u06cc\u0627\u0646 "
            "\u062f\u0631 \u062f\u06cc\u062a\u0627\u0633\u062a \u0627\u0641\u0633\u0631\u062f\u06af\u06cc \u0686\u0642\u062f\u0631 \u0627\u0633\u062a\u061f"
        )

        assert "student_depression" in r.tables
        assert "student_depression.cgpa_10" in r.columns
        assert "university_student_mental_health.cgpa_mid" not in r.columns
        assert "country_prevalence_long.disorder" not in r.columns

    def test_social_media_and_mental_health_rating_aliases(self, linker):
        social = linker.link(
            "\u0645\u06cc\u0627\u0646\u06af\u06cc\u0646 \u0633\u0627\u0639\u0627\u062a "
            "\u0634\u0628\u06a9\u0647\u200c\u0647\u0627\u06cc \u0627\u062c\u062a\u0645\u0627\u0639\u06cc "
            "\u062f\u0627\u0646\u0634\u062c\u0648\u06cc\u0627\u0646 \u0686\u0642\u062f\u0631 \u0627\u0633\u062a\u061f"
        )
        rating = linker.link(
            "\u0645\u06cc\u0627\u0646\u06af\u06cc\u0646 \u0631\u062a\u0628\u0647 "
            "\u0633\u0644\u0627\u0645\u062a \u0631\u0648\u0627\u0646 \u062f\u0627\u0646\u0634\u062c\u0648\u06cc\u0627\u0646 "
            "\u0686\u0642\u062f\u0631 \u0627\u0633\u062a\u061f"
        )

        assert "student_habits_performance.social_media_hours" in social.columns
        assert "student_habits_performance.mental_health_rating" in rating.columns

    def test_general_dataset_context_prefers_general_table(self, linker):
        r = linker.link(
            "\u0645\u06cc\u0627\u0646\u06af\u06cc\u0646 \u0646\u0645\u0631\u0647 "
            "\u0627\u0636\u0637\u0631\u0627\u0628 \u062f\u0631 \u062f\u06cc\u062a\u0627\u0633\u062a "
            "\u0639\u0645\u0648\u0645\u06cc \u0686\u0642\u062f\u0631 \u0627\u0633\u062a\u061f"
        )

        assert r.tables == ["mental_health_general"]
        assert "mental_health_general.anxiety_score" in r.columns
        assert "country_prevalence_long.disorder" not in r.columns

    def test_student_depression_analysis_context_prefers_student_depression_table(self, linker):
        r = linker.link(
            "\u062f\u0631\u0635\u062f \u0627\u0641\u0633\u0631\u062f\u06af\u06cc "
            "\u062f\u0627\u0646\u0634\u062c\u0648\u06cc\u0627\u0646 \u062f\u0631 \u0647\u0631 "
            "\u062c\u0646\u0633\u06cc\u062a \u0686\u0642\u062f\u0631 \u0627\u0633\u062a\u061f"
        )

        assert r.tables == ["student_depression"]
        assert "student_depression.gender" in r.columns
        assert "student_depression.depression_flag" in r.columns
        assert "mental_health_general.depression_score" not in r.columns


class TestConfidence:
    def test_high(self, linker):
        r = linker.link("میانگین نمره افسردگی دانشجوهای زن")
        assert r.confidence > 0.5

    def test_low(self, linker):
        r = linker.link("آب و هوای تهران")
        assert r.confidence < 0.5
