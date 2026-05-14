from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.core.query_ir import QueryIR


@dataclass(frozen=True)
class ConceptMapping:
    concept_id: str
    aliases: list[str] = field(default_factory=list)
    implied_metrics: list[str] = field(default_factory=list)
    implied_filters: list[dict[str, Any]] = field(default_factory=list)
    implied_dimensions: list[str] = field(default_factory=list)


class ConceptRegistry:
    """Registry mapping abstract user concepts to explicit schema constraints for QueryIR."""

    def __init__(self) -> None:
        self.concepts: dict[str, ConceptMapping] = {
            "depression": ConceptMapping(
                concept_id="depression",
                aliases=["افسردگی", "افسرده", "دیپرشن", "depression", "depressed"],
                implied_metrics=["phq9_score", "depression_flag"],
                implied_filters=[{"column": "depression_flag", "operator": "=", "value": 1}],
            ),
            "anxiety": ConceptMapping(
                concept_id="anxiety",
                aliases=["اضطراب", "نگرانی", "استرس", "anxiety"],
                implied_metrics=["gad7_score"],
                implied_filters=[{"column": "anxiety_flag", "operator": "=", "value": 1}],
            ),
            "female": ConceptMapping(
                concept_id="female",
                aliases=["زن", "دختر", "زنان", "female", "women"],
                implied_filters=[{"column": "gender", "operator": "=", "value": "Female"}],
                implied_dimensions=["gender"],
            ),
            "male": ConceptMapping(
                concept_id="male",
                aliases=["مرد", "پسر", "مردان", "male", "men"],
                implied_filters=[{"column": "gender", "operator": "=", "value": "Male"}],
                implied_dimensions=["gender"],
            ),
            "student": ConceptMapping(
                concept_id="student",
                aliases=["دانشجو", "دانش آموز", "محصل", "student", "students"],
                implied_filters=[], # General context, usually no hard filter
            ),
            "cgpa": ConceptMapping(
                concept_id="cgpa",
                aliases=["معدل", "نمره", "gpa", "cgpa"],
                implied_metrics=["cgpa"],
            ),
            "sleep": ConceptMapping(
                concept_id="sleep",
                aliases=["خواب", "کیفیت خواب", "sleep"],
                implied_metrics=["sleep_quality", "sleep_hours"],
            ),
        }

    def resolve_concepts(self, terms: list[str]) -> list[ConceptMapping]:
        """Find concepts matching any of the extracted terms."""
        matched: list[ConceptMapping] = []
        for term in terms:
            term_lower = term.lower()
            for concept in self.concepts.values():
                if term_lower in concept.aliases and concept not in matched:
                    matched.append(concept)
        return matched

    def enrich_qir(self, qir: QueryIR, terms: list[str]) -> QueryIR:
        """Enrich a QueryIR object with constraints derived from concepts."""
        concepts = self.resolve_concepts(terms)
        for concept in concepts:
            # Only add implied metrics if no metric is currently defined and it's an aggregation/ranking
            # or add them generally if requested. (Here we just append missing ones).
            for metric in concept.implied_metrics:
                if metric not in qir.metrics:
                    qir.metrics.append(metric)
            
            # Dimensions
            for dim in concept.implied_dimensions:
                if dim not in qir.dimensions:
                    qir.dimensions.append(dim)
                    
            # Filters
            for filt in concept.implied_filters:
                # Basic dedup
                if not any(f.get("column") == filt.get("column") and f.get("value") == filt.get("value") for f in qir.filters):
                    qir.filters.append(filt)
                    
        return qir
