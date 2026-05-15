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
