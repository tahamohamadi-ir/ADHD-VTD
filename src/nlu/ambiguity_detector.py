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
    GENERIC_PATTERNS = [
        "یه آمار کلی", "یک آمار کلی", "آمار کلی", "وضعیت چطوره", "وضعیت دانشجوها",
        "یه چیزی نشون بده", "چیزی نشان بده", "top 10", "کدوم بهتره", "بهترین ها", "بدترین ها",
        "تحلیل کن", "داشبورد بساز", "خلاصه بده",
    ]
    REQUIRED_METRIC_HINTS = [
        "افسردگی", "اضطراب", "خواب", "cgpa", "معدل", "نمره", "درمان", "ریسک", "استرس", "شیوع", "حضور", "exam"
    ]

    def __init__(self) -> None:
        self.normalizer = PersianNormalizer()

    def detect(self, text: str) -> AmbiguityDecision:
        norm = self.normalizer.normalize_text(text).lower()
        reasons: list[str] = []
        score = 0.0

        if any(p in norm for p in self.GENERIC_PATTERNS):
            reasons.append("Generic request without clear metric/dataset.")
            score += 0.6

        if "top 10" in norm or "ده تا" in norm or "۱۰" in norm:
            if not any(h in norm for h in self.REQUIRED_METRIC_HINTS):
                reasons.append("Ranking request without ranking metric.")
                score += 0.4

        if len(norm.split()) <= 3 and not any(h in norm for h in self.REQUIRED_METRIC_HINTS):
            reasons.append("Very short request without enough semantic anchors.")
            score += 0.4

        is_amb = score >= 0.5
        clarification = None
        if is_amb:
            clarification = "لطفاً مشخص کنید کدام شاخص یا دیتاست مدنظر است؛ مثلاً افسردگی، اضطراب، خواب، CGPA، درمان‌جویی، یا شیوع جهانی."
        return AmbiguityDecision(is_amb, min(score, 1.0), reasons, clarification)
