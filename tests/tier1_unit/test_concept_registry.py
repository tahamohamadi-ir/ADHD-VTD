from src.schema.concept_registry import ConceptRegistry
from src.core.query_ir import QueryIR


class TestConceptRegistry:
    def test_depression_mapping(self):
        registry = ConceptRegistry()
        concepts = registry.resolve_concepts(["افسرده", "خواب"])
        assert len(concepts) == 2
        
        ids = [c.concept_id for c in concepts]
        assert "depression" in ids
        assert "sleep" in ids

    def test_enrich_qir(self):
        registry = ConceptRegistry()
        qir = QueryIR()
        
        qir = registry.enrich_qir(qir, ["دانشجو", "دختر", "افسردگی"])
        
        assert "depression_flag" in qir.metrics or "phq9_score" in qir.metrics
        assert "gender" in qir.dimensions
        
        # filters check
        has_depression_filter = any(f["column"] == "depression_flag" and f["value"] == 1 for f in qir.filters)
        has_female_filter = any(f["column"] == "gender" and f["value"] == "Female" for f in qir.filters)
        
        assert has_depression_filter
        assert has_female_filter
