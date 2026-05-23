from __future__ import annotations

from dataclasses import dataclass, field

try:
    from src.nlu.persian_normalizer import PersianNormalizer
except Exception:  # pragma: no cover
    from persian_normalizer import PersianNormalizer

@dataclass(frozen=True)
class AmbiguityDecision:
    is_ambiguous: bool
    score: float
    reasons: list[str] = field(default_factory=list)
    clarification_question: str | None = None

class AmbiguityDetector:
    """Detect ambiguous queries that cannot produce reliable SQL.

    Checks include:
    - Generic requests without clear metric/dataset
    - Ranking requests ("best/worst") without a ranking metric
    - Chart requests without a measure or dimension
    - Very short requests without enough semantic anchors
    """

    GENERIC_PATTERNS = [
        "یه آمار کلی", "یک آمار کلی", "آمار کلی", "وضعیت چطوره", "وضعیت دانشجوها",
        "یه چیزی نشون بده", "چیزی نشان بده", "top 10", "کدوم بهتره", "بهترین ها", "بدترین ها",
        "تحلیل کن", "تحلیل", "داشبورد بساز", "خلاصه بده", "خلاصه نمایش بده", "خلاصه",
    ]
    VAGUE_PROFILE_PATTERNS = [
        "مشخصات", "ویژگی", "پروفایل", "چگونه است", "چطور است", "چه کسانی"
    ]
    IMPOSSIBLE_PATTERNS = [
        "علت و معلول", "رابطه علت", "توصیه", "پیش‌بینی", "score واحد", "وزن دهی", "اصلاح‌شده", "مدل بساز", "صفر فرض کن"
    ]
    VAGUE_TERMS = [
        "پرریسک", "مشکل", "خوب"
    ]
    REQUIRED_METRIC_HINTS = [
        "افسردگی", "اضطراب", "خواب", "cgpa", "معدل", "نمره", "درمان", "ریسک", "استرس", "شیوع", "حضور", "exam",
        "phq9", "gad7", "bdi", "sleep", "score", "gpa", "depression", "anxiety",
        "eating_disorder", "schizophrenia", "bipolar", "prevalence", "country", "countries",
        "change", "quartile", "percentile", "germany", "italy", "united kingdom", "sweden", "japan", "brazil", "iran",
        "remote", "treatment", "benefits", "تعداد", "توزیع",
    ]

    # Ranking terms that need a metric to be actionable
    RANKING_PATTERNS = [
        "بهترین", "بدترین", "بیشترین", "کمترین", "بالاترین", "پایین‌ترین", "پایین ترین",
        "اولین", "آخرین", "top", "best", "worst", "highest", "lowest",
    ]

    # Chart request patterns
    CHART_PATTERNS = [
        "نمودار", "چارت", "chart", "graph", "plot", "رسم کن", "ترسیم",
        "bar chart", "pie chart", "line chart", "histogram",
        "نمودار میله ای", "نمودار دایره ای", "نمودار خطی",
    ]

    # Dimension/measure hints for chart requests
    DIMENSION_HINTS = [
        "بر اساس", "تفکیک", "گروه", "جنسیت", "سال", "کشور", "رشته", "دانشکده",
        "gender", "year", "country", "department", "age", "سن", "مقطع",
    ]

    def __init__(self) -> None:
        self.normalizer = PersianNormalizer()

    def detect(self, text: str) -> AmbiguityDecision:
        norm = self.normalizer.normalize_text(text).lower()
        reasons: list[str] = []
        score = 0.0
        has_metric = any(h in norm for h in self.REQUIRED_METRIC_HINTS)

        # Data-aware signals
        _data_signals = [
            "دیتاست", "dataset", "survey", "دیتابیس", "جدول", "table",
            "محل کار", "workplace", "دانشجو", "student", "کشور", "country",
            "پاسخ", "response", "رکورد", "record", "نمونه", "sample",
            "اشتغال", "employment", "وضعیت", "شغلی",
        ]
        has_data_signal = any(s in norm for s in _data_signals)

        # 1. Generic request without clear metric/dataset
        if any(p in norm for p in self.GENERIC_PATTERNS) and not has_metric and not has_data_signal:
            reasons.append("Generic request without clear metric/dataset.")
            score += 0.6

        # 2. Ranking without specific metric ("بهترین" without knowing "best at what?")
        has_ranking = any(p in norm for p in self.RANKING_PATTERNS)
        if has_ranking and not has_metric:
            reasons.append("Ranking request (best/worst) without specifying the ranking metric.")
            score += 0.5

        # 3. Top-N without metric (existing check, enhanced)
        if "top 10" in norm or "ده تا" in norm or "10" in norm:
            if not has_metric:
                reasons.append("Top-N ranking request without ranking metric.")
                score += 0.4

        # 4. Chart request without measure or dimension
        has_chart = any(p in norm for p in self.CHART_PATTERNS)
        has_dimension = any(d in norm for d in self.DIMENSION_HINTS)
        if has_chart:
            if not has_metric and not has_dimension:
                reasons.append("Chart request without specifying measure or dimension.")
                score += 0.5
            elif not has_metric:
                reasons.append("Chart request without specifying a measure/metric.")
                score += 0.3

        # 5. Very short request without enough semantic anchors
        if len(norm.split()) <= 3 and not has_metric:
            reasons.append("Very short request without enough semantic anchors.")
            score += 0.5

        # 6. Vague profile request without dimension
        has_vague_profile = any(p in norm for p in self.VAGUE_PROFILE_PATTERNS)
        if has_vague_profile and not has_dimension and not has_data_signal:
            reasons.append("Vague profile request without specifying which characteristics to look at.")
            score += 0.6
            
        # 7. Impossible tasks
        if any(p in norm for p in self.IMPOSSIBLE_PATTERNS):
            reasons.append("Impossible or non-SQL task requested.")
            score += 0.8
            
        # 8. Vague terms
        has_vague_terms = any(p in norm for p in self.VAGUE_TERMS)
        if has_vague_terms and not has_dimension:
            reasons.append("Vague terms used without precise definition.")
            score += 0.5

        is_amb = score >= 0.5
        clarification = None
        if is_amb:
            clarification = self._build_clarification(reasons, has_ranking, has_chart, has_vague_profile, has_vague_terms)
        return AmbiguityDecision(is_amb, min(score, 1.0), reasons, clarification)

    def _build_clarification(self, reasons: list[str], has_ranking: bool, has_chart: bool, has_vague: bool = False, has_vague_terms: bool = False) -> str:
        """Build a context-appropriate clarification question in Persian."""
        if has_vague_terms:
            return "لطفاً منظور دقیق خود را از کلماتی مانند «عملکرد» یا «پرریسک» مشخص کنید تا قابل اندازه‌گیری باشد."
        if has_ranking:
            return (
                "لطفاً مشخص کنید بر اساس چه شاخصی رتبه‌بندی انجام شود؛ "
                "مثلاً بالاترین نمره افسردگی، بهترین معدل، یا بیشترین ساعت خواب."
            )
        if has_chart:
            return (
                "لطفاً مشخص کنید چه شاخصی و بر اساس چه بعدی نمودار رسم شود؛ "
                "مثلاً نمودار توزیع افسردگی بر اساس جنسیت، یا روند اضطراب بر اساس سال."
            )
        if has_vague:
            return (
                "این سوال خیلی کلی است. لطفاً مشخص کنید به دنبال کدام ویژگی‌ها هستید "
                "(مثلاً میانگین معدل، سن، جنسیت، یا ساعات خواب)؟"
            )
        return (
            "لطفاً مشخص کنید کدام شاخص یا دیتاست مدنظر است؛ "
            "مثلاً افسردگی، اضطراب، خواب، CGPA، درمان‌جویی، یا شیوع جهانی."
        )
