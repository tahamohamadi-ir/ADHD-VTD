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
