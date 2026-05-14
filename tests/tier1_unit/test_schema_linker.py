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

class TestConfidence:
    def test_high(self, linker):
        r = linker.link("میانگین نمره افسردگی دانشجوهای زن")
        assert r.confidence > 0.5

    def test_low(self, linker):
        r = linker.link("آب و هوای تهران")
        assert r.confidence < 0.5
