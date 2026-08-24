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

    def test_multiple_statements_rejected(self, validator):
        result = validator.validate(
            "SELECT COUNT(*) FROM student_depression; DROP TABLE student_depression"
        )

        assert not result.ok
        assert any(issue.code == "MULTIPLE_STATEMENTS" for issue in result.issues)

    def test_sql_comments_rejected(self, validator):
        result = validator.validate("SELECT COUNT(*) FROM student_depression -- hide condition")

        assert not result.ok
        assert any(issue.code == "SQL_COMMENT" for issue in result.issues)


class TestSafeAcceptance:
    def test_select(self, validator):
        assert validator.validate("SELECT COUNT(*) FROM student_depression").ok

    def test_cte(self, validator):
        sql = "WITH d AS (SELECT * FROM student_depression) SELECT COUNT(*) FROM d"
        assert validator.validate(sql).ok

    def test_group_by(self, validator):
        assert validator.validate(
            "SELECT gender, COUNT(*) FROM student_depression GROUP BY gender"
        ).ok


class TestSelectStar:
    def test_raw_star_rejected(self):
        v = SQLSafetyValidator(allow_select_star=False)
        assert not v.validate("SELECT * FROM student_depression").ok

    def test_table_star_rejected(self):
        v = SQLSafetyValidator(allow_select_star=False)
        result = v.validate("SELECT student_depression.* FROM student_depression")

        assert not result.ok
        assert any(issue.code == "SELECT_STAR" for issue in result.issues)


class TestRawRowLimit:
    def test_raw_row_projection_requires_limit_by_default(self, validator):
        result = validator.validate("SELECT age, gender FROM student_depression")

        assert not result.ok
        assert any(issue.code == "RAW_ROW_LIMIT_REQUIRED" for issue in result.issues)

    def test_bounded_raw_row_projection_is_allowed(self, validator):
        result = validator.validate("SELECT age, gender FROM student_depression LIMIT 20")

        assert result.ok

    def test_executor_can_disable_raw_limit_guard(self):
        validator = SQLSafetyValidator(require_limit_for_raw=False)

        result = validator.validate("SELECT age, gender FROM student_depression")

        assert result.ok


class TestSensitiveRowLevelDisclosure:
    def test_sensitive_row_level_columns_rejected(self, validator):
        result = validator.validate(
            "SELECT student_depression_id, suicidal_thoughts "
            "FROM student_depression WHERE suicidal_thoughts = 1 LIMIT 10"
        )

        assert not result.ok
        codes = {issue.code for issue in result.issues}
        assert "PRIVACY_IDENTIFIER_PROJECTION" in codes
        assert "PRIVACY_SENSITIVE_ROW_LEVEL" in codes

    def test_sensitive_aggregate_distribution_allowed(self, validator):
        result = validator.validate(
            "SELECT suicidal_thoughts, COUNT(*) AS n "
            "FROM student_depression GROUP BY suicidal_thoughts"
        )

        assert result.ok

    def test_public_country_prevalence_timeseries_allowed(self, validator):
        result = validator.validate(
            "WITH pivoted AS ("
            "SELECT year, "
            "MAX(CASE WHEN disorder = 'depression' THEN prevalence_pct END) AS depression_pct, "
            "MAX(CASE WHEN disorder = 'anxiety' THEN prevalence_pct END) AS anxiety_pct "
            "FROM country_prevalence_long WHERE country_name = 'Iran' GROUP BY year"
            "), enriched AS ("
            "SELECT year, depression_pct, anxiety_pct, "
            "anxiety_pct - depression_pct AS anxiety_minus_depression, "
            "depression_pct - LAG(depression_pct) OVER (ORDER BY year) AS depression_yoy, "
            "anxiety_pct - LAG(anxiety_pct) OVER (ORDER BY year) AS anxiety_yoy "
            "FROM pivoted"
            ") "
            "SELECT year, ROUND(depression_pct, 3) AS depression_pct, "
            "ROUND(anxiety_pct, 3) AS anxiety_pct, "
            "ROUND(anxiety_minus_depression, 3) AS anxiety_minus_depression, "
            "ROUND(depression_yoy, 3) AS depression_yoy_change, "
            "ROUND(anxiety_yoy, 3) AS anxiety_yoy_change "
            "FROM enriched ORDER BY year"
        )

        assert result.ok

    def test_identifier_aggregate_allowed(self, validator):
        result = validator.validate(
            "SELECT COUNT(student_depression_id) AS n FROM student_depression"
        )

        assert result.ok
