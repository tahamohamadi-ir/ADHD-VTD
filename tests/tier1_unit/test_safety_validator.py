"""Unit tests for SQLSafetyValidator."""
from __future__ import annotations
import pytest
from src.sql_validation.safety_validator import SQLSafetyValidator

@pytest.fixture
def validator():
    return SQLSafetyValidator()

class TestUnsafeRejection:
    def test_insert(self, validator):
        assert not validator.validate("INSERT INTO t VALUES (1)").ok

    def test_drop(self, validator):
        assert not validator.validate("DROP TABLE t").ok

    def test_delete(self, validator):
        assert not validator.validate("DELETE FROM t WHERE id=1").ok

    def test_update(self, validator):
        assert not validator.validate("UPDATE t SET x=1").ok

class TestSafeAcceptance:
    def test_select(self, validator):
        assert validator.validate("SELECT COUNT(*) FROM student_depression").ok

    def test_cte(self, validator):
        sql = "WITH d AS (SELECT * FROM student_depression) SELECT COUNT(*) FROM d"
        assert validator.validate(sql).ok

    def test_group_by(self, validator):
        assert validator.validate("SELECT gender, COUNT(*) FROM student_depression GROUP BY gender").ok

class TestSelectStar:
    def test_raw_star_rejected(self):
        v = SQLSafetyValidator(allow_select_star=False)
        assert not v.validate("SELECT * FROM student_depression").ok
