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
    safety_label: str = "safe"
    ambiguity_score: float = 0.0

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
            return IntentDecision(
                IntentLabel.UNSAFE_QUERY,
                1.0,
                False,
                ExpectedAction.REFUSE_UNSAFE_SQL,
                safety.reasons,
                safety.label,
                0.0,
            )

        norm = self.normalizer.normalize_text(text).lower()
        reasons: list[str] = []

        clarification_reason = self._deterministic_clarification_reason(norm, text.lower())
        if clarification_reason:
            return IntentDecision(
                IntentLabel.AMBIGUOUS_QUERY,
                0.90,
                False,
                ExpectedAction.ASK_CLARIFICATION,
                [clarification_reason],
                "safe",
                0.90,
            )

        if self._is_chart_advice(norm):
            return IntentDecision(
                IntentLabel.CHART_QUERY,
                0.90,
                False,
                ExpectedAction.ANSWER_CHART_RECOMMENDATION,
                ["Chart recommendation advice detected - no SQL needed."],
            )

        if self._is_no_sql_meta_advice(norm):
            return IntentDecision(
                IntentLabel.DEFINITION_QUERY,
                0.90,
                False,
                ExpectedAction.ANSWER_WITHOUT_SQL,
                ["Meta/advice request detected - no SQL needed."],
            )

        # 2. Ambiguity gate
        amb = self.ambiguity.detect(text)
        if amb.is_ambiguous and not self._has_strong_sql_signal(norm):
            return IntentDecision(
                IntentLabel.AMBIGUOUS_QUERY,
                amb.score,
                False,
                ExpectedAction.ASK_CLARIFICATION,
                amb.reasons,
                "safe",
                amb.score,
            )
        if amb.is_ambiguous:
            reasons.extend([f"Ambiguity override: {reason}" for reason in amb.reasons])

        # 3. Definition or Advice query — "X چیست", "چطور" (methodology)
        # Methodology advice
        if any(x in norm for x in ["چطور", "چگونه", "چطوری"]) and any(y in norm for y in ["انتخاب", "استفاده", "بهتر", "روش", "راهنمایی"]):
            return IntentDecision(
                IntentLabel.DEFINITION_QUERY, 0.90, False, ExpectedAction.ANSWER_WITHOUT_SQL,
                ["Methodological advice question detected — no SQL needed."],
            )

        definition_cues = ["چیست", "چیه", "چی هست", "تعریف", "یعنی چی", "what is", "define", "definition"]
        if any(x in norm for x in definition_cues):
            sql_cues = ["میانگین", "شیوع", "روند", "تغییر", "مقایسه", "نرخ", "بیشترین", "کمترین", "توزیع", "تعداد", "سال", "ماه", "دیتاست", "دیتابیس", "جدول", "درصد"]
            if any(s in norm for s in sql_cues):
                pass # Fall through to SQL
            elif len(norm.split()) <= 5:
                return IntentDecision(
                    IntentLabel.DEFINITION_QUERY, 0.80, False, ExpectedAction.ANSWER_WITHOUT_SQL,
                    ["Short definition/explanation question detected — no SQL needed."],
                )
            else:
                pass # Default to SQL if it's long and has 'چیست'

        # 3.5 Chart Recommendation Advice
        if any(x in norm for x in ["چه نموداری", "کدوم نمودار", "کدام نمودار", "چه چارتی", "چی بهتره", "چی بذارم", "پیشنهاد بده"]):
            return IntentDecision(
                IntentLabel.CHART_QUERY, 0.90, False, ExpectedAction.ANSWER_CHART_RECOMMENDATION,
                ["Chart recommendation advice detected — no SQL needed."]
            )

        chart_advice_cues = [
            "چه نموداری",
            "کدام نمودار",
            "چی بکشم",
            "چه visual",
            "چه نوع نمایش",
            "نمایش امن",
            "pie chart",
            "scatter",
            "bar",
            "visual",
        ]
        if any(cue in norm for cue in chart_advice_cues):
            return IntentDecision(
                IntentLabel.CHART_QUERY,
                0.90,
                False,
                ExpectedAction.ANSWER_CHART_RECOMMENDATION,
                ["Chart recommendation advice detected - no SQL needed."],
            )

        no_sql_advice_cues = [
            "توضیح بدم",
            "توضیح بده",
            "بنویس",
            "طراحی کن",
            "چه داستانی",
            "داستان‌سرایی",
            "روایت",
            "چه ترتیب",
            "چه sequence",
            "چه کار کنم",
            "معیارهای evaluation",
            "معماری rag",
            "برای مقاله",
            "validity",
            "threat",
            "evaluation",
            "nl2sql",
            "schema linking",
            "query generation",
        ]
        no_sql_subject_cues = [
            "داشبورد",
            "پروژه",
            "مدل",
            "مقاله",
            "مدیر",
            "محیط کار",
            "داده",
            "دیتاست",
            "جهانی",
            "uncertainty",
            "policy maturity",
            "treatment rate",
            "rag",
            "nl2sql",
            "schema linking",
            "query generation",
            "evaluation",
        ]
        if any(cue in norm for cue in no_sql_advice_cues) and any(cue in norm for cue in no_sql_subject_cues):
            return IntentDecision(
                IntentLabel.DEFINITION_QUERY,
                0.90,
                False,
                ExpectedAction.ANSWER_WITHOUT_SQL,
                ["Meta/advice request detected - no SQL needed."],
            )

        # 4. Comparison query — "مقایسه" / "تفاوت" / "compare"
        if any(x in norm for x in [
            "مقایسه", "تفاوت", "فرق", "compare", "comparison", "versus", "vs",
            "در مقابل", "نسبت به", "بیشتر از", "کمتر از", "تضاد", "بین",
        ]):
            return IntentDecision(
                IntentLabel.COMPARISON_QUERY, 0.85, True, ExpectedAction.GENERATE_SQL,
                ["Comparison between groups/metrics detected."],
            )

        # 5. Raw retrieval query — "لیست" / "show all" / "list"
        if any(x in norm for x in [
            "لیست", "فهرست", "همه", "نمایش بده", "نشان بده", "بده",
            "list all", "show all", "show me", "get all", "retrieve",
            "خلاصه کن", "خلاصه", "چطورن", "چطوره",
        ]):
            # Only if no stronger analytical signal; Persian requests often end with "give/show it".
            if not any(x in norm for x in [
                "میانگین",
                "تعداد",
                "درصد",
                "نرخ",
                "روند",
                "تغییر",
                "افزایش",
                "رتبه",
                "بیشترین",
                "کمترین",
                "آخرین سال",
                "توزیع",
                "تفکیک",
                "بر اساس",
                "اختلال",
                "avg",
                "average",
                "count",
                "sum",
                "percent",
                "rate",
                "trend",
                "rank",
                "group by",
            ]):
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

        if any(x in norm for x in ["matrix", "\u0645\u0627\u062a\u0631\u06cc\u0633", "Ù…Ø§ØªØ±ÛŒØ³"]):
            return IntentDecision(
                IntentLabel.GROUPING_QUERY, 0.75, True, ExpectedAction.GENERATE_SQL,
                ["Matrix cue mapped to analytical SQL grouping."],
            )

        # 7. Dashboard/storytelling
        if any(x in norm for x in ["داشبورد", "داستان", "روایت", "story"]):
            return IntentDecision(
                IntentLabel.GROUPING_QUERY, 0.75, True, ExpectedAction.GENERATE_SQL,
                ["Dashboard/storytelling cue mapped to analytical SQL grouping."],
            )

        # 8. Ranking. Rank requests can also mention latest-year or aggregate metrics.
        if any(x in norm for x in ["رتبه", "بیشترین", "کمترین", "top", "اول", "بالاترین", "بهترین", "بدترین"]):
            return IntentDecision(IntentLabel.RANKING_QUERY, 0.75, True, ExpectedAction.GENERATE_SQL, ["Ranking cue."])

        # 9. Time series / trend
        if any(x in norm for x in ["روند", "سال", "آخرین سال", "time", "trend", "طی سال"]):
            return IntentDecision(
                IntentLabel.TREND_QUERY, 0.75, True, ExpectedAction.GENERATE_SQL,
                ["Temporal cue."],
            )

        # 10. Rate / percentage
        if any(x in norm for x in ["درصد", "نرخ", "rate", "%"]):
            return IntentDecision(IntentLabel.RATE_QUERY, 0.85, True, ExpectedAction.GENERATE_SQL, ["Rate/percentage cue."])

        # 11. Aggregation
        if any(x in norm for x in ["میانگین", "مجموع", "avg", "average", "sum", "min", "max"]):
            return IntentDecision(IntentLabel.AGGREGATION_QUERY, 0.9, True, ExpectedAction.GENERATE_SQL, ["Aggregation cue."])

        # 12. Count
        if any(x in norm for x in ["تعداد", "چند", "count"]):
            return IntentDecision(IntentLabel.COUNT_QUERY, 0.85, True, ExpectedAction.GENERATE_SQL, ["Count cue."])

        # 13. Grouping / distribution
        if any(x in norm for x in ["توزیع", "تفکیک", "بر اساس", "گروه", "group by"]):
            return IntentDecision(IntentLabel.GROUPING_QUERY, 0.75, True, ExpectedAction.GENERATE_SQL, ["Grouping cue."])

        # Default
        return IntentDecision(
            IntentLabel.UNKNOWN, 0.55, True, ExpectedAction.GENERATE_SQL,
            reasons or ["Default safe SQL-capable request."],
        )

    def _is_chart_advice(self, norm: str) -> bool:
        chart_advice_cues = [
            "چه نموداری",
            "کدام نمودار",
            "چی بکشم",
            "چه visual",
            "چه نوع نمایش",
            "نمایش امن",
            "pie chart",
            "scatter",
            "bar",
            "visual",
        ]
        return any(cue in norm for cue in chart_advice_cues)

    def _is_no_sql_meta_advice(self, norm: str) -> bool:
        no_sql_advice_cues = [
            "توضیح بدم",
            "توضیح بده",
            "بنویس",
            "طراحی کن",
            "چه داستانی",
            "داستان‌سرایی",
            "روایت",
            "چه ترتیب",
            "چه sequence",
            "چه کار کنم",
            "معیارهای evaluation",
            "معماری rag",
            "برای مقاله",
            "validity",
            "threat",
            "evaluation",
            "nl2sql",
            "schema linking",
            "query generation",
        ]
        no_sql_subject_cues = [
            "داشبورد",
            "پروژه",
            "مدل",
            "مقاله",
            "مدیر",
            "محیط کار",
            "داده",
            "دیتاست",
            "جهانی",
            "uncertainty",
            "policy maturity",
            "treatment rate",
            "rag",
            "nl2sql",
            "schema linking",
            "query generation",
            "evaluation",
        ]
        return any(cue in norm for cue in no_sql_advice_cues) and any(cue in norm for cue in no_sql_subject_cues)

    def _has_strong_sql_signal(self, norm: str) -> bool:
        """Detect clear analytical data requests that should not abstain as vague."""
        metric_cues = [
            "\u0645\u06cc\u0627\u0646\u06af\u06cc\u0646",
            "\u062f\u0631\u0635\u062f",
            "\u0646\u0631\u062e",
            "\u062a\u0639\u062f\u0627\u062f",
            "\u062a\u0648\u0632\u06cc\u0639",
            "\u0634\u06cc\u0648\u0639",
            "\u062a\u063a\u06cc\u06cc\u0631",
            "\u0631\u0648\u0646\u062f",
            "\u0631\u062a\u0628\u0647",
            "\u0628\u06cc\u0634\u062a\u0631\u06cc\u0646",
            "\u06a9\u0645\u062a\u0631\u06cc\u0646",
            "\u0628\u0627\u0644\u0627\u062a\u0631\u06cc\u0646",
            "\u067e\u0627\u06cc\u06cc\u0646\u200c\u062a\u0631\u06cc\u0646",
            "\u0635\u062f\u06a9",
            "\u0622\u062e\u0631\u06cc\u0646 \u0633\u0627\u0644",
            "\u0622\u062e\u0631\u06cc\u0646 \u0645\u0642\u062f\u0627\u0631",
            "\u0686\u0646\u062f",
            "\u0686\u0646\u062f \u0646\u0641\u0631",
            "\u062e\u0644\u0627\u0635\u0647",
            "\u062a\u062d\u0644\u06cc\u0644",
            "\u06a9\u0646\u0627\u0631 \u0647\u0645",
            "avg",
            "average",
            "count",
            "rate",
            "percent",
            "prevalence",
            "summary",
            "trend",
            "rank",
            "top",
            "highest",
            "lowest",
            "quartile",
            "percentile",
        ]
        data_cues = [
            "\u062f\u06cc\u062a\u0627\u0633\u062a",
            "\u062f\u06cc\u062a\u0627\u0628\u06cc\u0633",
            "\u062c\u062f\u0648\u0644",
            "\u062f\u0627\u0634\u0628\u0648\u0631\u062f",
            "\u06a9\u0634\u0648\u0631",
            "\u0633\u0627\u0644",
            "\u0634\u0647\u0631",
            "\u062f\u0627\u0646\u0634\u062c\u0648",
            "\u062c\u0647\u0627\u0646\u06cc",
            "\u0646\u0638\u0631\u0633\u0646\u062c\u06cc",
            "\u0645\u062d\u06cc\u0637 \u06a9\u0627\u0631",
            "\u0633\u0627\u0628\u0642\u0647 \u062e\u0627\u0646\u0648\u0627\u062f\u06af\u06cc",
            "\u0645\u0634\u06a9\u0644 \u0631\u0648\u0627\u0646",
            "\u0622\u0645\u0627\u062f\u06af\u06cc \u0633\u0627\u0632\u0645\u0627\u0646\u06cc",
            "\u0645\u0635\u0627\u062d\u0628\u0647 \u0633\u0644\u0627\u0645\u062a \u0631\u0648\u0627\u0646",
            "\u0647\u0631 \u0627\u062e\u062a\u0644\u0627\u0644",
            "\u0647\u0645\u0647 \u0627\u062e\u062a\u0644\u0627\u0644",
            "\u0627\u062e\u062a\u0644\u0627\u0644",
            "\u0627\u0641\u0633\u0631\u062f\u06af\u06cc",
            "\u0627\u0636\u0637\u0631\u0627\u0628",
            "\u0627\u0633\u062a\u0631\u0633",
            "\u062e\u0648\u0627\u0628",
            "dataset",
            "survey",
            "workplace",
            "table",
            "dashboard",
            "country",
            "countries",
            "year",
            "city",
            "student",
            "disorder",
            "depression",
            "anxiety",
            "stress",
            "sleep",
            "gender",
            "diet_quality",
            "internet_quality",
            "parental_education_level",
            "social_media",
            "remote_work",
            "treatment",
            "benefits",
        ]
        group_cues = [
            "\u0628\u0631 \u0627\u0633\u0627\u0633",
            "\u0628\u0647 \u062a\u0641\u06a9\u06cc\u06a9",
            "\u062a\u0641\u06a9\u06cc\u06a9",
            "\u06af\u0631\u0648\u0647",
            "\u0628\u0631\u0627\u06cc \u0647\u0631",
            "\u0647\u0631 \u06a9\u062f\u0627\u0645",
            "group by",
            "by ",
            "per ",
            "for each",
        ]
        named_entities = [
            "iran",
            "germany",
            "italy",
            "japan",
            "brazil",
            "sweden",
            "united kingdom",
            "india",
            "china",
            "france",
            "canada",
            "\u0627\u06cc\u0631\u0627\u0646",
            "\u0622\u0644\u0645\u0627\u0646",
            "\u0627\u06cc\u062a\u0627\u0644\u06cc\u0627",
            "\u0698\u0627\u067e\u0646",
            "\u0628\u0631\u0632\u06cc\u0644",
            "\u0633\u0648\u0626\u062f",
            "\u0647\u0646\u062f",
            "\u0686\u06cc\u0646",
            "\u0641\u0631\u0627\u0646\u0633\u0647",
            "\u06a9\u0627\u0646\u0627\u062f\u0627",
        ]

        has_metric = any(cue in norm for cue in metric_cues)
        has_data = any(cue in norm for cue in data_cues) or any(entity in norm for entity in named_entities)
        has_grouping = any(cue in norm for cue in group_cues)
        return (has_metric and has_data) or (has_metric and has_grouping) or ("dashboard" in norm and has_data)

    def _deterministic_clarification_reason(self, norm: str, raw_lower: str) -> str | None:
        """Catch high-risk Persian ambiguity patterns before SQL routing."""
        if any(
            cue in norm
            for cue in [
                "\u062f\u0627\u0646\u0634\u062c\u0648\u0647\u0627\u06cc \u0628\u062f",
                "\u06cc\u0647 \u0686\u06cc\u0632\u06cc",
                "\u0648\u0636\u0639\u06cc\u062a \u062f\u0627\u0646\u0634\u062c\u0648\u0647\u0627",
            ]
        ):
            return "Vague Persian user phrase needs metric/entity clarification."

        if (
            "\u0628\u0686\u0647\u200c\u0647\u0627" in raw_lower
            and "\u062a\u0648 \u062f\u06cc\u062a\u0627" in norm
        ):
            return "Colloquial entity reference needs clarification before SQL generation."

        if any(cue in norm for cue in ["\u062d\u0627\u0644\u0627", "\u0647\u0645\u0648\u0646 \u062a\u062d\u0644\u06cc\u0644"]):
            return "Context-dependent follow-up cannot be answered without prior turn context."

        if "\u0627\u062b\u0631 \u0647\u0645\u0632\u0645\u0627\u0646 \u0686\u0646\u062f \u0639\u0627\u0645\u0644" in norm:
            return "Multi-factor effect request does not specify the factors or model."

        if "normalize \u06a9\u0646" in norm or "\u0645\u0646\u0627\u0628\u0639 \u0642\u0627\u0628\u0644 \u0645\u0642\u0627\u06cc\u0633\u0647" in norm:
            return "Normalization/preprocessing policy is underspecified."

        if "\u0639\u0644\u062a" in norm and "\u062b\u0627\u0628\u062a \u06a9\u0646" in norm:
            return "Causal proof request needs clarification and cannot be answered as direct SQL."

        if "\u0628\u0647\u062a\u0631\u06cc\u0646 \u0646\u062a\u06cc\u062c\u0647 \u0639\u0644\u0645\u06cc" in norm or (
            "\u0628\u0631\u0627\u06cc \u0645\u0642\u0627\u0644\u0647" in norm
            and "\u0627\u0633\u062a\u062e\u0631\u0627\u062c \u06a9\u0646" in norm
        ):
            return "Research-result mining request needs a pre-declared analysis target."

        if "\u062f\u0627\u062f\u0647 \u067e\u0631\u062a" in norm:
            return "Outlier handling needs a metric and exclusion policy before SQL generation."

        return None
