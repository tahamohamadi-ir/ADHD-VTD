from src.sql_validation.join_validator import SQLJoinValidator


class TestSQLJoinValidator:
    def test_valid_join(self):
        validator = SQLJoinValidator()
        sql = "SELECT * FROM country_prevalence_long JOIN country_prevalence_wide ON country_prevalence_long.country_name = country_prevalence_wide.country_name"
        result = validator.validate(sql)
        assert result.ok

    def test_invalid_cross_domain_join(self):
        validator = SQLJoinValidator()
        sql = "SELECT * FROM student_depression JOIN mental_health_general ON student_depression.gender = mental_health_general.gender"
        result = validator.validate(sql)
        assert not result.ok
        assert any(i.code == "ILLEGAL_JOIN" for i in result.issues)

    def test_cte_ignored(self):
        validator = SQLJoinValidator()
        sql = "WITH cte AS (SELECT * FROM student_depression) SELECT * FROM cte JOIN student_depression ON cte.gender = student_depression.gender"
        result = validator.validate(sql)
        assert result.ok

    def test_implicit_cross_join(self):
        validator = SQLJoinValidator()
        sql = "SELECT * FROM student_depression, student_habits_performance"
        result = validator.validate(sql)
        assert not result.ok
        assert any(i.code == "ILLEGAL_JOIN" for i in result.issues)
