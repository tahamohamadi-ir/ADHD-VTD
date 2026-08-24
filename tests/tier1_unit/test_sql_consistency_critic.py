from __future__ import annotations

from src.evaluation.sql_consistency_critic import analyze_question_sql_consistency


def _codes(question: str, sql: str) -> set[str]:
    report = analyze_question_sql_consistency(question, sql)
    return {issue.code for issue in report.issues}


def test_consistency_critic_flags_rate_question_without_rate_computation():
    codes = _codes(
        "What is the depression rate by sleep category?",
        "SELECT sleep_duration_category, COUNT(*) AS n FROM student_depression GROUP BY sleep_duration_category",
    )

    assert "QUESTION_SQL_MISSING_RATE_COMPUTATION" in codes


def test_consistency_critic_accepts_grouped_rate_shape():
    report = analyze_question_sql_consistency(
        "What is the depression rate by sleep category?",
        "SELECT sleep_duration_category, COUNT(*) AS n, "
        "ROUND(100.0 * SUM(depression_flag) / COUNT(*), 2) AS rate_pct "
        "FROM student_depression GROUP BY sleep_duration_category",
    )

    assert report.passed is True
    assert report.issues == []


def test_consistency_critic_accepts_window_partition_as_segmented_result():
    report = analyze_question_sql_consistency(
        "\u0631\u062a\u0628\u0647 \u0627\u06cc\u0631\u0627\u0646 "
        "\u0628\u0631\u0627\u06cc \u0647\u0631 \u0627\u062e\u062a\u0644\u0627\u0644 "
        "\u062a\u0648 \u0622\u062e\u0631\u06cc\u0646 \u0633\u0627\u0644 \u0686\u0646\u062f\u0647\u061f",
        "WITH r AS (SELECT country_name, disorder, prevalence_pct, "
        "RANK() OVER (PARTITION BY disorder ORDER BY prevalence_pct DESC) AS rnk "
        "FROM country_prevalence_long WHERE year = (SELECT MAX(year) FROM country_prevalence_long)) "
        "SELECT disorder, ROUND(prevalence_pct, 4) AS iran_prevalence, rnk AS iran_rank "
        "FROM r WHERE country_name = 'Iran' ORDER BY iran_rank",
    )

    assert report.passed is True
    assert report.issues == []


def test_consistency_critic_flags_above_average_filter_without_avg_threshold():
    codes = _codes(
        "Show risks for people with stress above average and sleep below average.",
        "SELECT mental_health_risk, COUNT(*) AS n FROM mental_health_general GROUP BY mental_health_risk",
    )

    assert "QUESTION_SQL_MISSING_AVERAGE_THRESHOLD" in codes


def test_consistency_critic_flags_fixed_threshold_when_question_asks_average_threshold():
    codes = _codes(
        "Show risks for people with stress above average and sleep below average.",
        "SELECT mental_health_risk, COUNT(*) AS n, AVG(stress_level) AS avg_stress, "
        "AVG(sleep_hours) AS avg_sleep FROM mental_health_general "
        "WHERE stress_level > 4 AND sleep_hours < 7 GROUP BY mental_health_risk",
    )

    assert "QUESTION_SQL_MISSING_AVERAGE_THRESHOLD" in codes


def test_consistency_critic_flags_risk_profile_missing_context_averages():
    codes = _codes(
        "Show risks for people with stress above average and sleep below average.",
        "SELECT mental_health_risk, COUNT(*) AS n "
        "FROM mental_health_general "
        "WHERE stress_level > (SELECT AVG(stress_level) FROM mental_health_general) "
        "AND sleep_hours < (SELECT AVG(sleep_hours) FROM mental_health_general) "
        "GROUP BY mental_health_risk",
    )

    assert "QUESTION_SQL_MISSING_RISK_CONTEXT_AVERAGES" in codes
    assert "QUESTION_SQL_MISSING_RISK_GROUPING" not in codes


def test_consistency_critic_accepts_risk_profile_with_group_count_and_context_averages():
    report = analyze_question_sql_consistency(
        "Show risks for people with stress above average and sleep below average.",
        "SELECT mental_health_risk, COUNT(*) AS n, "
        "AVG(stress_level) AS avg_stress, AVG(sleep_hours) AS avg_sleep "
        "FROM mental_health_general "
        "WHERE stress_level > (SELECT AVG(stress_level) FROM mental_health_general) "
        "AND sleep_hours < (SELECT AVG(sleep_hours) FROM mental_health_general) "
        "GROUP BY mental_health_risk",
    )

    assert report.passed is True
    assert report.issues == []


def test_consistency_critic_flags_comparative_single_group_filter_without_baseline():
    codes = _codes(
        "Do high risk people seek treatment more?",
        "SELECT AVG(seeks_treatment) * 100.0 FROM mental_health_general WHERE mental_health_risk = 'High'",
    )

    assert "QUESTION_SQL_MISSING_COMPARISON_BASELINE" in codes


def test_consistency_critic_accepts_comparative_grouped_risk_query():
    report = analyze_question_sql_consistency(
        "Do high risk people seek treatment more?",
        "SELECT mental_health_risk, AVG(seeks_treatment) * 100.0 AS treatment_rate "
        "FROM mental_health_general GROUP BY mental_health_risk ORDER BY treatment_rate DESC",
    )

    assert report.passed is True
    assert report.issues == []


def test_consistency_critic_flags_change_question_without_change_measure():
    codes = _codes(
        "Show quartiles of change in eating disorder prevalence since 1990.",
        "SELECT AVG(prevalence_pct) FROM country_prevalence_long WHERE disorder='eating_disorder'",
    )

    assert "QUESTION_SQL_MISSING_CHANGE_MEASURE" in codes
    assert "QUESTION_SQL_MISSING_BINNING" in codes


def test_consistency_critic_warning_for_top_question_without_ordering_does_not_fail():
    report = analyze_question_sql_consistency(
        "Show the top countries by anxiety prevalence.",
        "SELECT country_name, prevalence_pct FROM country_prevalence_long LIMIT 10",
    )

    assert report.passed is True
    assert [issue.severity for issue in report.issues] == ["warning"]
