from __future__ import annotations

from types import SimpleNamespace

from src.core.query_ir import QueryIR
from src.sql_validation.shape_validator import SQLShapeValidator


def _schema() -> dict[str, SimpleNamespace]:
    return {
        "country_prevalence_long": SimpleNamespace(
            columns=[
                SimpleNamespace(name="country_name"),
                SimpleNamespace(name="year"),
                SimpleNamespace(name="is_country_like"),
                SimpleNamespace(name="disorder"),
                SimpleNamespace(name="prevalence_pct"),
            ]
        ),
        "country_prevalence_wide": SimpleNamespace(
            columns=[
                SimpleNamespace(name="country_name"),
                SimpleNamespace(name="year"),
                SimpleNamespace(name="is_country_like"),
                SimpleNamespace(name="eating_disorder_pct"),
            ]
        ),
        "mental_health_general": SimpleNamespace(
            columns=[
                SimpleNamespace(name="mental_health_risk"),
                SimpleNamespace(name="stress_level"),
                SimpleNamespace(name="sleep_hours"),
            ]
        ),
        "student_depression": SimpleNamespace(
            columns=[
                SimpleNamespace(name="sleep_duration_category"),
                SimpleNamespace(name="dietary_habits"),
                SimpleNamespace(name="depression_flag"),
                SimpleNamespace(name="cgpa_10"),
            ]
        ),
    }


def test_shape_validator_rejects_sqlite_unsupported_percentile_function():
    result = SQLShapeValidator().validate(
        "SELECT PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY eating_disorder_pct) FROM country_prevalence_wide",
        question="dashboard eating_disorder percentiles",
        qir=QueryIR(task_type="grouping_query"),
        schema=_schema(),
    )

    assert not result.ok
    assert any(issue.code == "UNSUPPORTED_SQLITE_ANALYTIC_FUNCTION" for issue in result.issues)


def test_shape_validator_rejects_latest_year_scalar_for_global_change_dashboard():
    question = (
        "\u062f\u0627\u0634\u0628\u0648\u0631\u062f "
        "\u062a\u063a\u06cc\u06cc\u0631 \u062c\u0647\u0627\u0646\u06cc "
        "eating_disorder: "
        "\u0645\u06cc\u0627\u0646\u06af\u06cc\u0646\u060c "
        "\u0635\u062f\u06a9\u200c\u0647\u0627 \u0648 "
        "\u0628\u06cc\u0634\u062a\u0631\u06cc\u0646 "
        "\u062a\u063a\u06cc\u06cc\u0631 \u06a9\u0634\u0648\u0631\u0647\u0627 "
        "\u0631\u0627 \u0628\u062f\u0647."
    )

    result = SQLShapeValidator().validate(
        "SELECT AVG(eating_disorder_pct) FROM country_prevalence_wide WHERE year=(SELECT MAX(year) FROM country_prevalence_wide)",
        question=question,
        qir=QueryIR(task_type="grouping_query"),
        schema=_schema(),
    )

    assert not result.ok
    codes = {issue.code for issue in result.issues}
    assert "ANALYTICAL_SHAPE_MISSING_LONG_PREVALENCE_TABLE" in codes
    assert "ANALYTICAL_SHAPE_MISSING_BINNING" in codes


def test_shape_validator_accepts_sqlite_binned_global_change_shape():
    sql = (
        "WITH endpoints AS ("
        "SELECT country_name, "
        "MAX(CASE WHEN year = 1990 THEN prevalence_pct END) AS value_baseline, "
        "MAX(CASE WHEN year = (SELECT MAX(year) FROM country_prevalence_long) THEN prevalence_pct END) AS value_latest "
        "FROM country_prevalence_long WHERE disorder='eating_disorder' AND is_country_like=1 GROUP BY country_name"
        "), changes AS ("
        "SELECT country_name, value_latest - value_baseline AS change_pct_point FROM endpoints"
        "), ranked AS ("
        "SELECT *, NTILE(4) OVER (ORDER BY change_pct_point) AS change_quartile FROM changes"
        ") SELECT change_quartile, COUNT(*) AS country_count, AVG(change_pct_point) AS avg_change "
        "FROM ranked GROUP BY change_quartile"
    )

    result = SQLShapeValidator().validate(
        sql,
        question="dashboard global change eating_disorder percentiles",
        qir=QueryIR(task_type="grouping_query"),
        schema=_schema(),
    )

    assert result.ok


def test_shape_validator_rejects_row_level_risk_result_for_average_filters():
    result = SQLShapeValidator().validate(
        "SELECT mental_health_risk FROM mental_health_general WHERE stress_level > (SELECT AVG(stress_level) FROM mental_health_general)",
        question="risks for people with stress above average and sleep below average",
        qir=QueryIR(task_type="aggregation_query"),
        schema=_schema(),
    )

    assert not result.ok
    assert any(issue.code == "ANALYTICAL_SHAPE_MISSING_RISK_GROUPING" for issue in result.issues)


def test_shape_validator_rejects_grouped_risk_summary_without_requested_average_filters():
    result = SQLShapeValidator().validate(
        (
            "SELECT mental_health_risk, COUNT(*) AS n, AVG(stress_level) AS avg_stress, "
            "AVG(sleep_hours) AS avg_sleep FROM mental_health_general "
            "WHERE stress_level IS NOT NULL AND sleep_hours IS NOT NULL "
            "GROUP BY mental_health_risk"
        ),
        question="risks for people with stress above average and sleep below average",
        qir=QueryIR(task_type="aggregation_query"),
        schema=_schema(),
    )

    assert not result.ok
    assert any(issue.code == "ANALYTICAL_SHAPE_MISSING_RISK_AVERAGE_FILTERS" for issue in result.issues)
    assert not any(issue.code == "ANALYTICAL_SHAPE_MISSING_RISK_KEY" for issue in result.issues)


def test_shape_validator_accepts_risk_key_after_aggregate_columns():
    result = SQLShapeValidator().validate(
        (
            "SELECT AVG(stress_level) AS avg_stress, AVG(sleep_hours) AS avg_sleep, "
            "mental_health_risk, COUNT(*) AS n FROM mental_health_general "
            "WHERE stress_level > (SELECT AVG(stress_level) FROM mental_health_general) "
            "AND sleep_hours < (SELECT AVG(sleep_hours) FROM mental_health_general) "
            "GROUP BY mental_health_risk ORDER BY n DESC"
        ),
        question="risks for people with stress above average and sleep below average",
        qir=QueryIR(task_type="aggregation_query"),
        schema=_schema(),
    )

    assert result.ok


def test_shape_validator_accepts_grouped_risk_summary_with_requested_average_filters():
    result = SQLShapeValidator().validate(
        (
            "SELECT mental_health_risk, COUNT(*) AS n, AVG(stress_level) AS avg_stress, "
            "AVG(sleep_hours) AS avg_sleep FROM mental_health_general "
            "WHERE stress_level > (SELECT AVG(stress_level) FROM mental_health_general) "
            "AND sleep_hours < (SELECT AVG(sleep_hours) FROM mental_health_general) "
            "GROUP BY mental_health_risk ORDER BY n DESC"
        ),
        question="risks for people with stress above average and sleep below average",
        qir=QueryIR(task_type="aggregation_query"),
        schema=_schema(),
    )

    assert result.ok


def test_shape_validator_accepts_general_risk_profile_without_stress_sleep_averages():
    result = SQLShapeValidator().validate(
        (
            "SELECT mental_health_risk, COUNT(*) AS total, "
            "ROUND(AVG(depression_score), 2) AS avg_depression_score, "
            "ROUND(AVG(anxiety_score), 2) AS avg_anxiety_score "
            "FROM mental_health_general GROUP BY mental_health_risk"
        ),
        question="average depression and anxiety based on mental health risk level",
        qir=QueryIR(task_type="aggregation_query"),
        schema=_schema(),
    )

    assert result.ok


def test_shape_validator_accepts_grouped_sleep_depression_rate_without_gold_extra_columns():
    sql = (
        "SELECT sleep_duration_category AS group_value, COUNT(*) AS n, "
        "ROUND(100.0 * SUM(depression_flag) / COUNT(*), 2) AS rate_pct "
        "FROM student_depression WHERE sleep_duration_category IS NOT NULL "
        "GROUP BY sleep_duration_category ORDER BY rate_pct DESC LIMIT 15"
    )

    result = SQLShapeValidator().validate(
        sql,
        question="sleep category depression rate",
        qir=QueryIR(task_type="rate_query"),
        schema=_schema(),
    )

    assert result.ok


def test_shape_validator_accepts_equivalent_not_null_filter_for_grouped_sleep_rate():
    sql = (
        "SELECT sleep_duration_category AS group_value, COUNT(*) AS n, "
        "ROUND(100.0 * SUM(depression_flag) / COUNT(*), 2) AS depression_rate_pct "
        "FROM student_depression WHERE NOT sleep_duration_category IS NULL "
        "GROUP BY sleep_duration_category ORDER BY depression_rate_pct DESC LIMIT 15"
    )

    result = SQLShapeValidator().validate(
        sql,
        question="sleep category depression rate",
        qir=QueryIR(task_type="rate_query"),
        schema=_schema(),
    )

    assert result.ok


def test_shape_validator_rejects_grouped_sleep_rate_without_depression_flag_formula():
    result = SQLShapeValidator().validate(
        (
            "SELECT sleep_duration_category AS group_value, COUNT(*) AS n, "
            "ROUND(100.0 * COUNT(*) / COUNT(*), 2) AS rate_pct "
            "FROM student_depression WHERE sleep_duration_category IS NOT NULL "
            "GROUP BY sleep_duration_category ORDER BY rate_pct DESC LIMIT 15"
        ),
        question="sleep category depression rate",
        qir=QueryIR(task_type="rate_query"),
        schema=_schema(),
    )

    assert not result.ok
    codes = {issue.code for issue in result.issues}
    assert "ANALYTICAL_SHAPE_MISSING_RATE_NUMERATOR" in codes


def test_shape_validator_rejects_wrong_table_columns_for_sleep_diet_matrix():
    result = SQLShapeValidator().validate(
        (
            "SELECT sleep_hours, diet_quality, COUNT(*) AS total, AVG(cgpa_10) AS avg_cgpa_10 "
            "FROM student_depression GROUP BY sleep_hours, diet_quality"
        ),
        question="matrix sleep and diet for depression and CGPA",
        qir=QueryIR(task_type="grouping_query"),
        schema=_schema(),
    )

    assert not result.ok
    codes = {issue.code for issue in result.issues}
    assert "ANALYTICAL_SHAPE_MISSING_SLEEP_DIET_KEYS" in codes
    assert "ANALYTICAL_SHAPE_WRONG_TABLE_SLEEP_DIET_COLUMNS" in codes


def test_shape_validator_accepts_sleep_diet_depression_cgpa_matrix():
    result = SQLShapeValidator().validate(
        (
            "SELECT sleep_duration_category, dietary_habits, COUNT(*) AS n, "
            "ROUND(100.0 * SUM(depression_flag) / COUNT(*), 2) AS depression_rate_pct, "
            "ROUND(AVG(cgpa_10), 2) AS avg_cgpa "
            "FROM student_depression WHERE sleep_duration_category IS NOT NULL "
            "AND dietary_habits IS NOT NULL GROUP BY sleep_duration_category, dietary_habits "
            "HAVING COUNT(*) >= 50 ORDER BY depression_rate_pct DESC"
        ),
        question="matrix sleep and diet for depression and CGPA",
        qir=QueryIR(task_type="grouping_query"),
        schema=_schema(),
    )

    assert result.ok


def test_shape_validator_rejects_sleep_diet_matrix_without_support_threshold_and_metric_sort():
    result = SQLShapeValidator().validate(
        (
            "SELECT sleep_duration_category, dietary_habits, COUNT(*) AS n, "
            "ROUND(100.0 * SUM(depression_flag) / COUNT(*), 2) AS depression_rate_pct, "
            "ROUND(AVG(cgpa_10), 2) AS avg_cgpa "
            "FROM student_depression WHERE sleep_duration_category IS NOT NULL "
            "AND dietary_habits IS NOT NULL GROUP BY sleep_duration_category, dietary_habits "
            "ORDER BY n DESC LIMIT 100"
        ),
        question="matrix sleep and diet for depression and CGPA",
        qir=QueryIR(task_type="grouping_query"),
        schema=_schema(),
    )

    assert not result.ok
    codes = {issue.code for issue in result.issues}
    assert "ANALYTICAL_SHAPE_MISSING_MATRIX_SUPPORT_THRESHOLD" in codes
    assert "ANALYTICAL_SHAPE_MISSING_PRIMARY_METRIC_SORT" in codes
