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
