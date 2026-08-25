"""Unit tests for SQLSchemaValidator."""

from __future__ import annotations
import pytest
from src.sql_validation.schema_validator import SQLSchemaValidator


@pytest.fixture
def validator():
    return SQLSchemaValidator()


class TestFakeColumns:
    def test_unknown_column(self, validator):
        r = validator.validate("SELECT fake_column FROM student_depression")
        assert not r.ok
        assert any("fake_column" in i.message for i in r.issues)

    def test_unknown_table(self, validator):
        r = validator.validate("SELECT id FROM nonexistent_table")
        assert not r.ok


class TestOldTables:
    def test_old_table_detected(self, validator):
        r = validator.validate("SELECT * FROM individuals_core")
        assert not r.ok


class TestValidSQL:
    def test_valid_query(self, validator):
        r = validator.validate("SELECT COUNT(*) FROM student_depression")
        assert r.ok


class TestRepairHints:
    def test_unknown_table_close_match_yields_hint(self, validator):
        r = validator.validate("SELECT id FROM student_depressio")
        assert not r.ok
        table_hints = [h for h in r.repair_hints if h.action == "use_table"]
        assert len(table_hints) == 1
        assert table_hints[0].suggestion == "student_depression"
        assert table_hints[0].confidence >= 0.6

    def test_unknown_column_close_match_yields_hint(self, validator):
        r = validator.validate("SELECT AVG(academic_presure) FROM student_depression")
        assert not r.ok
        col_hints = [h for h in r.repair_hints if h.action == "replace_column"]
        assert col_hints and "academic_pressure" in col_hints[0].suggestion

    def test_no_hint_without_close_match(self, validator):
        r = validator.validate("SELECT zzqqxx FROM zzqqww")
        assert not r.ok
        assert r.repair_hints == ()

    def test_duplicate_unknown_columns_yield_single_hint(self, validator):
        r = validator.validate(
            "SELECT academic_presure FROM student_depression WHERE academic_presure > 3"
        )
        assert not r.ok
        col_hints = [h for h in r.repair_hints if h.action == "replace_column"]
        assert len(col_hints) == 1

    def test_valid_sql_has_no_hints(self, validator):
        r = validator.validate("SELECT academic_pressure FROM student_depression")
        assert r.ok
        assert r.repair_hints == ()
