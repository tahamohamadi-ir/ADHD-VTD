from __future__ import annotations

from dataclasses import dataclass, field

from src.nlu.persian_normalizer import PersianNormalizer
from src.nlu.safety_intent_detector import SafetyIntentDetector
from src.nlu.ambiguity_detector import AmbiguityDetector
from src.core.enums import IntentLabel, ExpectedAction

@dataclass(frozen=True)
class IntentDecision:
    intent: IntentLabel
    confidence: float
    should_generate_sql: bool
    expected_action: ExpectedAction
    reasons: list[str] = field(default_factory=list)

class IntentClassifier:
    """Rule-based intent classifier for VTD pipeline.

    Supports the following intent types:
    - unsafe: dangerous/injection queries → refuse
    - ambiguous: vague queries → ask clarification
    - definition_query: "X چیست" / "what is X" → answer without SQL
    - comparison_query: comparing groups/metrics
    - raw_retrieval_query: "list all" / "show records"
    - dashboard_or_storytelling: dashboard/narrative requests
    - time_series_query: temporal/trend queries
    - rate_query: percentage/rate queries
    - aggregation_query: average/sum/min/max
    - count_query: counting queries
    - grouping_query: distribution/breakdown queries
    - ranking_query: top-N/best/worst queries
    - chart_query: explicit chart/visualization requests
    - general_sql_query: default SQL-capable request
    """

    def __init__(self) -> None:
        self.normalizer = PersianNormalizer()
        self.safety = SafetyIntentDetector()
        self.ambiguity = AmbiguityDetector()

    def classify(self, text: str) -> IntentDecision:
        # 1. Safety gate: always first
        safety = self.safety.detect(text)
        if not safety.is_safe:
            return IntentDecision(IntentLabel.UNSAFE_QUERY, 1.0, False, ExpectedAction.REFUSE_UNSAFE_SQL, safety.reasons)

        # 2. Ambiguity gate
        amb = self.ambiguity.detect(text)
        if amb.is_ambiguous:
            return IntentDecision(IntentLabel.AMBIGUOUS_QUERY, amb.score, False, ExpectedAction.ASK_CLARIFICATION, amb.reasons)

        norm = self.normalizer.normalize_text(text).lower()
        reasons: list[str] = []

        # 3. Definition query — "X چیست" / "what is X" / "تعریف X"
        if any(x in norm for x in ["چیست", "چیه", "چی هست", "تعریف", "یعنی چی", "what is", "define", "definition"]):
            return IntentDecision(
                IntentLabel.DEFINITION_QUERY, 0.90, False, ExpectedAction.ANSWER_WITHOUT_SQL,
                ["Definition/explanation question detected — no SQL needed."],
            )

        # 4. Comparison query — "مقایسه" / "تفاوت" / "compare"
        if any(x in norm for x in [
            "مقایسه", "تفاوت", "فرق", "compare", "comparison", "versus", "vs",
            "در مقابل", "نسبت به", "بیشتر از", "کمتر از",
        ]):
            return IntentDecision(
                IntentLabel.COMPARISON_QUERY, 0.85, True, ExpectedAction.GENERATE_SQL,
                ["Comparison between groups/metrics detected."],
            )

        # 5. Raw retrieval query — "لیست" / "show all" / "list"
        if any(x in norm for x in [
            "لیست", "فهرست", "همه", "نمایش بده", "نشان بده", "بده",
            "list all", "show all", "show me", "get all", "retrieve",
        ]):
            # Only if no aggregation signal
            if not any(x in norm for x in ["میانگین", "تعداد", "avg", "count", "sum", "درصد"]):
                return IntentDecision(
                    IntentLabel.RAW_RETRIEVAL_QUERY, 0.70, True, ExpectedAction.GENERATE_SQL,
                    ["Raw data retrieval request — will need LIMIT enforcement."],
                )

        # 6. Chart/visualization query
        if any(x in norm for x in ["نمودار", "چارت", "chart", "graph", "plot", "رسم", "histogram"]):
            return IntentDecision(
                IntentLabel.CHART_QUERY, 0.80, True, ExpectedAction.GENERATE_SQL,
                ["Chart/visualization request detected."],
            )

        # 7. Dashboard/storytelling
        if any(x in norm for x in ["داشبورد", "داستان", "روایت", "story"]):
            return IntentDecision(
                IntentLabel.NON_SQL_REQUEST, 0.75, True, ExpectedAction.GENERATE_SQL,
                ["Dashboard/storytelling cue."],
            )

        # 8. Time series / trend
        if any(x in norm for x in ["روند", "سال", "آخرین سال", "time", "trend", "طی سال"]):
            return IntentDecision(
                IntentLabel.TREND_QUERY, 0.75, True, ExpectedAction.GENERATE_SQL,
                ["Temporal cue."],
            )

        # 9. Rate / percentage
        if any(x in norm for x in ["درصد", "نرخ", "rate", "%"]):
            return IntentDecision(IntentLabel.RATE_QUERY, 0.85, True, ExpectedAction.GENERATE_SQL, ["Rate/percentage cue."])

        # 10. Aggregation
        if any(x in norm for x in ["میانگین", "مجموع", "avg", "average", "sum", "min", "max"]):
            return IntentDecision(IntentLabel.AGGREGATION_QUERY, 0.9, True, ExpectedAction.GENERATE_SQL, ["Aggregation cue."])

        # 11. Count
        if any(x in norm for x in ["تعداد", "چند", "count"]):
            return IntentDecision(IntentLabel.COUNT_QUERY, 0.85, True, ExpectedAction.GENERATE_SQL, ["Count cue."])

        # 12. Grouping / distribution
        if any(x in norm for x in ["توزیع", "تفکیک", "بر اساس", "گروه", "group by"]):
            return IntentDecision(IntentLabel.GROUPING_QUERY, 0.75, True, ExpectedAction.GENERATE_SQL, ["Grouping cue."])

        # 13. Ranking
        if any(x in norm for x in ["رتبه", "بیشترین", "کمترین", "top", "اول", "بالاترین", "بهترین", "بدترین"]):
            return IntentDecision(IntentLabel.RANKING_QUERY, 0.75, True, ExpectedAction.GENERATE_SQL, ["Ranking cue."])

        # Default
        return IntentDecision(
            IntentLabel.UNKNOWN, 0.55, True, ExpectedAction.GENERATE_SQL,
            reasons or ["Default safe SQL-capable request."],
        )

