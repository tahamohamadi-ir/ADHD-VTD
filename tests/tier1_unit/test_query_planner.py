from src.schema.query_planner import QueryPlanner
from src.core.enums import IntentLabel
from src.core.types import SchemaLinkResult, LinkedColumn


class TestQueryPlanner:
    def test_build_qir_basic(self):
        planner = QueryPlanner()
        qir = planner.build_qir(
            normalized_question="میانگین معدل دختران افسرده چقدر است",
            extracted_terms=["معدل", "دختر", "افسرده"],
            intent=IntentLabel.AGGREGATION_QUERY,
        )

        assert qir.task_type == "aggregation_query"
        assert qir.should_generate_sql is True
        assert qir.expected_result_shape == "scalar"

        # Enriched by concepts
        assert "cgpa" in qir.metrics
        assert "phq9_score" in qir.metrics or "depression_flag" in qir.metrics
        assert any(f["column"] == "gender" and f["value"] == "Female" for f in qir.filters)

    def test_build_qir_unsafe(self):
        planner = QueryPlanner()
        qir = planner.build_qir(
            normalized_question="drop table students",
            extracted_terms=["drop", "table", "students"],
            intent=IntentLabel.UNSAFE_QUERY,
        )
        assert qir.should_generate_sql is False
        assert qir.task_type == "unsafe_query"

    def test_count_with_two_sided_grouping_becomes_tabular_qir(self):
        planner = QueryPlanner()
        schema_link = SchemaLinkResult(
            columns=[
                LinkedColumn(table="student_depression", column="depression_flag", score=0.95),
            ]
        )

        qir = planner.build_qir(
            normalized_question="show the count of depressed and non-depressed students",
            extracted_terms=["depressed"],
            intent=IntentLabel.COUNT_QUERY,
            schema_link=schema_link,
        )

        assert qir.task_type == "grouping_query"
        assert qir.expected_result_shape == "table"
        assert "depression_flag" in qir.dimensions
        assert not any(f["column"] == "depression_flag" and f["value"] == 1 for f in qir.filters)

    def test_grouped_rate_qir_keeps_dimension_and_binary_metric(self):
        planner = QueryPlanner()
        schema_link = SchemaLinkResult(
            tables=[],
            columns=[
                LinkedColumn(table="student_depression", column="gender", score=0.9),
                LinkedColumn(table="student_depression", column="depression_flag", score=0.9),
            ],
        )

        qir = planner.build_qir(
            normalized_question="depression rate by gender",
            extracted_terms=["depression", "gender"],
            intent=IntentLabel.RATE_QUERY,
            schema_link=schema_link,
        )

        assert qir.expected_result_shape == "table"
        assert "gender" in qir.dimensions
        assert "depression_flag" in qir.metrics
