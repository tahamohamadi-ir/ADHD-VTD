"""Unit tests for ValueLinker."""

from __future__ import annotations
import pytest
from src.schema.value_linker import ValueLinker


@pytest.fixture
def linker():
    return ValueLinker()


class TestGenderValues:
    def test_zan_to_female(self, linker):
        r = linker.resolve_for_column("دانشجوهای زن", "student_depression.gender")
        assert any(link.resolved_value == "Female" for link in r)

    def test_mard_to_male(self, linker):
        r = linker.resolve_for_column("دانشجوهای مرد", "student_depression.gender")
        assert any(link.resolved_value == "Male" for link in r)


class TestRiskLevels:
    def test_risk_bala(self, linker):
        r = linker.resolve_for_column("ریسک بالا", "mental_health_general.mental_health_risk")
        assert any(link.resolved_value == "High" for link in r)


class TestDepressionFlag:
    def test_afsorde_positive(self, linker):
        r = linker.resolve_for_column("افسرده", "student_depression.depression_flag")
        assert any(link.resolved_value == 1 for link in r)

    def test_negative_depression(self, linker):
        r = linker.resolve_for_column("بدون افسردگی", "student_depression.depression_flag")
        assert any(link.resolved_value == 0 for link in r)
