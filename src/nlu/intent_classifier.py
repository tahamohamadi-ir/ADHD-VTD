from __future__ import annotations

from dataclasses import dataclass, field

try:
    from src.nlu.persian_normalizer import PersianNormalizer
    from src.nlu.safety_intent_detector import SafetyIntentDetector
    from src.nlu.ambiguity_detector import AmbiguityDetector
except Exception:  # pragma: no cover
    from persian_normalizer import PersianNormalizer
    from safety_intent_detector import SafetyIntentDetector
    from ambiguity_detector import AmbiguityDetector

@dataclass(frozen=True)
class IntentDecision:
    intent: str
    confidence: float
    should_generate_sql: bool
    expected_action: str
    reasons: list[str] = field(default_factory=list)

class IntentClassifier:
    """Initial rule-based classifier. Good enough for Phase 1 before LLM routing."""

    def __init__(self) -> None:
        self.normalizer = PersianNormalizer()
        self.safety = SafetyIntentDetector()
        self.ambiguity = AmbiguityDetector()

    def classify(self, text: str) -> IntentDecision:
        safety = self.safety.detect(text)
        if not safety.is_safe:
            return IntentDecision("unsafe", 1.0, False, "refuse_unsafe_sql", safety.reasons)

        amb = self.ambiguity.detect(text)
        if amb.is_ambiguous:
            return IntentDecision("ambiguous", amb.score, False, "ask_clarification", amb.reasons)

        norm = self.normalizer.normalize_text(text).lower()
        reasons: list[str] = []

        if any(x in norm for x in ["داشبورد", "داستان", "روایت", "story"]):
            return IntentDecision("dashboard_or_storytelling", 0.75, True, "generate_sql", ["Dashboard/storytelling cue."])
        if any(x in norm for x in ["روند", "سال", "آخرین سال", "time", "trend"]):
            return IntentDecision("time_series_query", 0.75, True, "generate_sql", ["Temporal cue."])
        if any(x in norm for x in ["درصد", "نرخ", "rate", "%"]):
            return IntentDecision("rate_query", 0.85, True, "generate_sql", ["Rate/percentage cue."])
        if any(x in norm for x in ["میانگین", "avg", "average"]):
            return IntentDecision("aggregation_query", 0.9, True, "generate_sql", ["Average cue."])
        if any(x in norm for x in ["تعداد", "چند", "count"]):
            return IntentDecision("count_query", 0.85, True, "generate_sql", ["Count cue."])
        if any(x in norm for x in ["توزیع", "تفکیک", "بر اساس", "گروه"]):
            return IntentDecision("grouping_query", 0.75, True, "generate_sql", ["Grouping cue."])
        if any(x in norm for x in ["رتبه", "بیشترین", "کمترین", "top", "اول"]):
            return IntentDecision("ranking_query", 0.75, True, "generate_sql", ["Ranking cue."])

        return IntentDecision("general_sql_query", 0.55, True, "generate_sql", reasons or ["Default safe SQL-capable request."])
