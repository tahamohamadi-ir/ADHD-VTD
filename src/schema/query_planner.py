from __future__ import annotations

from src.core.enums import IntentLabel
from src.core.query_ir import QueryIR
from src.core.types import SchemaLinkResult
from src.schema.concept_registry import ConceptRegistry


class QueryPlanner:
    """Orchestrates NLU output and schema linking to build a QueryIR."""

    def __init__(self) -> None:
        self.registry = ConceptRegistry()

    def build_qir(
        self,
        normalized_question: str,
        extracted_terms: list[str],
        intent: IntentLabel,
        schema_link: SchemaLinkResult | None = None,
    ) -> QueryIR:
        """Build the structured QueryIR representation."""
        
        # 1. Base initialization from Intent
        qir = QueryIR(
            task_type=str(intent),
            should_generate_sql=intent not in (
                IntentLabel.UNSAFE_QUERY,
                IntentLabel.AMBIGUOUS_QUERY,
                IntentLabel.DEFINITION_QUERY,
                IntentLabel.NON_SQL_REQUEST,
            )
        )

        if intent in (IntentLabel.AGGREGATION_QUERY, IntentLabel.COUNT_QUERY, IntentLabel.RATE_QUERY):
            qir.expected_result_shape = "scalar"
        elif intent == IntentLabel.RAW_RETRIEVAL_QUERY:
            qir.expected_result_shape = "table"
        elif intent == IntentLabel.CHART_QUERY:
            qir.chart_intent = True

        # 2. Add elements from Schema Linking directly (if provided)
        if schema_link:
            for linked_col in schema_link.columns:
                # Naive heuristic: if confidence is high, consider it a metric or dimension
                if linked_col.score > 0.8:
                    if linked_col.column.endswith("_score") or linked_col.column in ["cgpa", "age"]:
                        if linked_col.column not in qir.metrics:
                            qir.metrics.append(linked_col.column)
                    elif linked_col.column not in qir.dimensions:
                        qir.dimensions.append(linked_col.column)

        # 3. Enrich using Semantic Concepts
        qir = self.registry.enrich_qir(qir, extracted_terms)

        return qir
