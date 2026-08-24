from __future__ import annotations

from types import SimpleNamespace

from src.core.query_ir import QueryIR
from src.generation.prompt_builder import PromptBuilder


def _schema(*table_names: str) -> dict[str, SimpleNamespace]:
    special_columns = {
        "student_depression": [
            ("sleep_duration_category", "TEXT"),
            ("dietary_habits", "TEXT"),
            ("depression_flag", "INTEGER"),
            ("family_history_mental_illness", "INTEGER"),
            ("cgpa_10", "REAL"),
        ],
        "country_prevalence_long": [
            ("country_name", "TEXT"),
            ("year", "INTEGER"),
            ("is_country_like", "INTEGER"),
            ("disorder", "TEXT"),
            ("prevalence_pct", "REAL"),
        ],
        "country_prevalence_wide": [
            ("country_name", "TEXT"),
            ("year", "INTEGER"),
            ("is_country_like", "INTEGER"),
            ("eating_disorder_pct", "REAL"),
        ],
        "mental_health_general": [
            ("mental_health_risk", "TEXT"),
            ("stress_level", "INTEGER"),
            ("sleep_hours", "REAL"),
        ],
    }
    return {
        table: SimpleNamespace(
            columns=[
                SimpleNamespace(name=name, type=col_type)
                for name, col_type in special_columns.get(
                    table,
                    [("id", "INTEGER"), ("value", "REAL")],
                )
            ]
        )
        for table in table_names
    }


def test_rate_prompt_adds_grouped_rate_shape_hint():
    question = (
        "\u062f\u0633\u062a\u0647\u200c\u0647\u0627\u06cc "
        "\u062e\u0648\u0627\u0628 \u0627\u0632 \u0646\u0638\u0631 "
        "\u0646\u0631\u062e \u0627\u0641\u0633\u0631\u062f\u06af\u06cc "
        "\u0686\u0647 \u0648\u0636\u0639\u06cc\u062a\u06cc "
        "\u062f\u0627\u0631\u0646\u062f\u061f"
    )

    prompt = PromptBuilder().build_sql_generation_prompt(
        question=question,
        qir=QueryIR(task_type="rate_query"),
        schema=_schema("student_depression"),
    )

    assert "Analysis Shape Guidance" in prompt
    assert "COUNT(*) AS n" in prompt
    assert "SUM(binary_flag) AS positives" in prompt
    assert "rate_pct" in prompt
    assert "LIMIT 15" in prompt
    assert "depression_flag as the binary flag" in prompt
    assert "Do not add unrelated context columns unless the user asks for them" in prompt


def test_dashboard_change_prompt_adds_long_table_and_quartile_hints():
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

    prompt = PromptBuilder().build_sql_generation_prompt(
        question=question,
        qir=QueryIR(task_type="grouping_query"),
        schema=_schema("country_prevalence_long", "country_prevalence_wide"),
    )

    assert "do not collapse the answer to a single scalar" in prompt
    assert "use country_prevalence_long" in prompt
    assert "MUST use country_prevalence_long" in prompt
    assert "Do not use prevalence_pct or disorder with country_prevalence_wide" in prompt
    assert "value_latest - value_baseline" in prompt
    assert "NTILE(4)" in prompt
    assert "SQLite does not support PERCENTILE_CONT" in prompt
    assert "country_count" in prompt


def test_risk_average_prompt_adds_grouped_risk_summary_hint():
    prompt = PromptBuilder().build_sql_generation_prompt(
        question="risks for people with stress above average and sleep below average",
        qir=QueryIR(task_type="aggregation_query"),
        schema=_schema("mental_health_general"),
    )

    assert "summarize by mental_health_risk" in prompt
    assert "GROUP BY mental_health_risk" in prompt
    assert "COUNT(*) AS n" in prompt
    assert "avg_stress" in prompt
    assert "avg_sleep" in prompt
    assert "Use subqueries for average thresholds" in prompt


def test_prompt_warns_not_to_copy_missing_few_shot_columns():
    prompt = PromptBuilder().build_sql_generation_prompt(
        question="show family history distribution for depressed students",
        qir=QueryIR(task_type="grouping_query"),
        schema=_schema("student_depression"),
        few_shot=[
            {
                "question": "show workplace family history",
                "sql": "SELECT family_history, COUNT(*) FROM workplace_mental_health_survey GROUP BY family_history;",
            }
        ],
    )

    assert "Do not copy table or column names from examples" in prompt
    assert "current schema column" in prompt
    assert "family_history_mental_illness" in prompt


def test_prompt_builder_reads_dict_style_schema_columns_for_specific_hints():
    schema = {
        "student_depression": {
            "columns": [
                {"name": "sleep_duration_category", "type": "TEXT"},
                {"name": "depression_flag", "type": "INTEGER"},
                {"name": "cgpa_10", "type": "REAL"},
            ]
        },
        "mental_health_general": {
            "columns": {
                "mental_health_risk": {"type": "TEXT"},
                "stress_level": {"type": "INTEGER"},
                "sleep_hours": {"type": "REAL"},
            }
        },
    }

    rate_prompt = PromptBuilder().build_sql_generation_prompt(
        question="sleep category depression rate",
        qir=QueryIR(task_type="rate_query"),
        schema=schema,
    )
    risk_prompt = PromptBuilder().build_sql_generation_prompt(
        question="risks for stress above average and sleep below average",
        qir=QueryIR(task_type="aggregation_query"),
        schema=schema,
    )

    assert "sleep_duration_category AS group_value" in rate_prompt
    assert "WHERE sleep_duration_category IS NOT NULL" in rate_prompt
    assert "Do not add unrelated context columns" in rate_prompt
    assert "avg_stress" in risk_prompt
    assert "avg_sleep" in risk_prompt


def test_matrix_prompt_adds_support_threshold_and_metric_sort_policy():
    prompt = PromptBuilder().build_sql_generation_prompt(
        question="matrix sleep and diet for depression and CGPA",
        qir=QueryIR(task_type="grouping_query"),
        schema=_schema("student_depression"),
    )

    assert "sleep_duration_category and dietary_habits" in prompt
    assert "HAVING COUNT(*) >= 50" in prompt
    assert "ORDER BY depression_rate_pct DESC" in prompt


def test_global_mental_health_prompt_warns_against_fake_disorder_filter():
    prompt = PromptBuilder().build_sql_generation_prompt(
        question=(
            "\u062a\u0639\u062f\u0627\u062f \u06a9\u0644 \u0631\u06a9\u0648\u0631\u062f\u0647\u0627\u06cc "
            "\u0634\u06cc\u0648\u0639 \u062c\u0647\u0627\u0646\u06cc \u0633\u0644\u0627\u0645\u062a "
            "\u0631\u0648\u0627\u0646 \u0686\u0642\u062f\u0631 \u0627\u0633\u062a\u061f"
        ),
        qir=QueryIR(task_type="count_query"),
        schema=_schema("country_prevalence_long"),
    )

    assert "generic 'mental health' is a topic label" in prompt
    assert "Do not add a disorder filter" in prompt


def test_each_disorder_prompt_adds_group_by_disorder_hint():
    prompt = PromptBuilder().build_sql_generation_prompt(
        question=(
            "\u0627\u0632 \u0647\u0631 \u0627\u062e\u062a\u0644\u0627\u0644 "
            "\u062a\u0648 \u062c\u062f\u0648\u0644 long \u0686\u0646\u062f "
            "\u0631\u06a9\u0648\u0631\u062f \u062f\u0627\u0631\u06cc\u0645\u061f"
        ),
        qir=QueryIR(task_type="count_query"),
        schema=_schema("country_prevalence_long"),
    )

    assert "GROUP BY disorder" in prompt
    assert "do not filter disorder" in prompt


def test_ranking_prompt_adds_order_by_and_limit_hint():
    prompt = PromptBuilder().build_sql_generation_prompt(
        question="top countries by average prevalence",
        qir=QueryIR(
            task_type="ranking_query",
            dimensions=["country_name"],
            metrics=["prevalence_pct"],
            expected_result_shape="table",
        ),
        schema=_schema("country_prevalence_long"),
    )

    assert "For ranking questions" in prompt
    assert "ORDER BY on that metric" in prompt
    assert "LIMIT 15" in prompt
    assert "This prompt is only for GROUPED questions" not in prompt


def test_raw_row_prompt_adds_limit_and_no_select_star_hint():
    prompt = PromptBuilder().build_sql_generation_prompt(
        question="show student records",
        qir=QueryIR(task_type="raw_retrieval_query", expected_result_shape="raw_rows"),
        schema=_schema("student_depression"),
    )

    assert "For raw row/list requests" in prompt
    assert "never use SELECT *" in prompt
    assert "LIMIT 100" in prompt
    assert "prefer clarification/refusal or an aggregate summary" in prompt
    assert "This prompt is only for GROUPED questions" not in prompt
