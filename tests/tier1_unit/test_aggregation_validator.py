from src.sql_validation.aggregation_validator import SQLAggregationValidator


class TestSQLAggregationValidator:
    def test_valid_aggregation(self):
        validator = SQLAggregationValidator()
        sql = "SELECT gender, AVG(cgpa_10) FROM student_depression GROUP BY gender"
        result = validator.validate(sql)
        assert result.ok

    def test_missing_group_by(self):
        validator = SQLAggregationValidator()
        sql = "SELECT gender, AVG(cgpa_10) FROM student_depression"
        result = validator.validate(sql)
        assert not result.ok
        assert any(i.code == "MISSING_GROUP_BY" for i in result.issues)

    def test_ungrouped_column(self):
        validator = SQLAggregationValidator()
        sql = "SELECT gender, city, AVG(cgpa_10) FROM student_depression GROUP BY gender"
        result = validator.validate(sql)
        assert not result.ok
        assert any(i.code == "UNGROUPED_COLUMN" for i in result.issues)

    def test_avg_on_text(self):
        validator = SQLAggregationValidator()
        sql = "SELECT AVG(gender) FROM student_depression"
        result = validator.validate(sql)
        assert not result.ok
        assert any(i.code == "INVALID_AGGREGATION" for i in result.issues)

    def test_sum_case_condition_on_text_column_is_valid(self):
        validator = SQLAggregationValidator()
        sql = (
            "SELECT SUM(CASE WHEN mental_health_risk = 'High' THEN 1 ELSE 0 END) AS high_risk_count "
            "FROM mental_health_general"
        )
        result = validator.validate(sql)
        assert result.ok

    def test_avg_case_condition_on_text_column_is_valid_when_value_is_numeric(self):
        validator = SQLAggregationValidator()
        sql = (
            "SELECT AVG(CASE WHEN disorder = 'depression' THEN prevalence_pct END) AS avg_depression "
            "FROM country_prevalence_long"
        )
        result = validator.validate(sql)
        assert result.ok

    def test_window_aggregate_does_not_require_group_by(self):
        validator = SQLAggregationValidator()
        sql = (
            "SELECT year, AVG(prevalence_pct) OVER (ORDER BY year ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) "
            "AS moving_avg_3y FROM country_prevalence_long"
        )
        result = validator.validate(sql)
        assert result.ok

    def test_case_alias_group_by_is_valid(self):
        validator = SQLAggregationValidator()
        sql = (
            "SELECT CASE WHEN age < 22 THEN 'Under 22' ELSE '22+' END AS age_group, "
            "COUNT(*) AS total FROM student_depression GROUP BY age_group"
        )
        result = validator.validate(sql)
        assert result.ok
