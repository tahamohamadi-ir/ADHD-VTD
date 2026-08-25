"""Tests for etude-mined prompt rules and feature presets."""

from __future__ import annotations

import pytest

from src.config import features
from src.core.query_ir import QueryIR
from src.generation import prompt_rules
from src.generation.prompt_builder import PromptBuilder
from src.generation.prompt_rules import (
    CORRECTION_EXAMPLES,
    render_correction_kb_block,
    render_simplicity_block,
)


SCHEMA = {
    "student_depression": {
        "columns": [
            {"name": "academic_pressure", "type": "REAL"},
            {"name": "gender", "type": "TEXT"},
        ]
    }
}


class TestSimplicityBlock:
    def test_disabled_returns_empty(self) -> None:
        assert render_simplicity_block(False) == []

    def test_enabled_returns_rule_line(self) -> None:
        lines = render_simplicity_block(True)
        assert len(lines) == 1
        assert "simplest SQL" in lines[0]


class TestCorrectionKbBlock:
    def test_disabled_returns_empty(self) -> None:
        assert render_correction_kb_block(False) == ""

    def test_enabled_lists_all_examples(self) -> None:
        text = render_correction_kb_block(True)
        for name, broken, _, fixed in CORRECTION_EXAMPLES:
            assert f"[{name}]" in text
            assert broken in text
            assert fixed in text


class TestPromptIntegration:
    def _builder(self) -> PromptBuilder:
        return PromptBuilder()

    def _qir(self) -> QueryIR:
        return QueryIR(question="تعداد دانشجویان؟", task_type="count_query")

    def test_repair_prompt_includes_kb_when_enabled(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(features, "REPAIR_CORRECTION_KB", True)
        prompt = self._builder().build_repair_prompt(
            question="q",
            schema=SCHEMA,
            qir=self._qir(),
            value_links={},
            previous_sql="SELECT x",
            validation_errors="Unknown column",
        )
        assert "[aggregate_in_where]" in prompt

    def test_repair_prompt_excludes_kb_when_disabled(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(features, "REPAIR_CORRECTION_KB", False)
        prompt = self._builder().build_repair_prompt(
            question="q",
            schema=SCHEMA,
            qir=self._qir(),
            value_links={},
            previous_sql="SELECT x",
            validation_errors="Unknown column",
        )
        assert "[aggregate_in_where]" not in prompt

    def test_generation_hint_added_when_simplicity_on(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        builder = self._builder()
        qir = self._qir()
        monkeypatch.setattr(features, "SIMPLICITY_FIRST_PROMPT", True)
        prompt = builder.build_sql_generation_prompt("q", qir, SCHEMA)
        assert "simplest SQL that answers the question" in prompt

    def test_generation_hint_absent_when_simplicity_off(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(features, "SIMPLICITY_FIRST_PROMPT", False)
        prompt = self._builder().build_sql_generation_prompt("q", self._qir(), SCHEMA)
        assert "simplest SQL that answers the question" not in prompt


class TestPresets:
    def test_minimal_disables_research_flags(self) -> None:
        p = features.preset_minimal()
        assert p["ENABLE_CAG"] is False
        assert p["ENABLE_MULTI_CANDIDATE_GENERATION"] is False
        assert p["SIMPLICITY_FIRST_PROMPT"] is False

    def test_full_enables_core_flags(self) -> None:
        p = features.preset_full()
        assert p["ENABLE_LANGGRAPH"] is True
        assert p["SIMPLICITY_FIRST_PROMPT"] is True

    def test_default_matches_module_constants(self) -> None:
        p = features.preset_default()
        assert p["SIMPLICITY_FIRST_PROMPT"] == features.SIMPLICITY_FIRST_PROMPT
        assert p["ENABLE_READ_ONLY_EXECUTION_ONLY"] is True


def test_examples_are_well_formed() -> None:
    for name, broken, logic, fixed in prompt_rules.CORRECTION_EXAMPLES:
        assert name and broken and logic and fixed
        assert broken.strip().lower() != fixed.strip().lower()
