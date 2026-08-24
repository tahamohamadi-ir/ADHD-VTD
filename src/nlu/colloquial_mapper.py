from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ColloquialMappingResult:
    original: str
    normalized: str
    matched_terms: dict[str, str] = field(default_factory=dict)


class ColloquialMapper:
    """Map colloquial Persian, Finglish, typos, and mixed English terms to canonical terms."""

    TERM_MAP: dict[str, str] = {
        # depression
        "افسوردگی": "افسردگی",
        "افسرده": "افسردگی",
        "دیپرشن": "افسردگی",
        "depression": "افسردگی",
        "depressed": "افسردگی",
        "depress": "افسردگی",
        # anxiety
        "اضتراب": "اضطراب",
        "استرس و اضطراب": "اضطراب",
        "anxiety": "اضطراب",
        "ezterab": "اضطراب",
        "esterab": "اضطراب",
        # panic
        "panik attack": "panic_attack",
        "panic attack": "panic_attack",
        "حمله پانیک": "panic_attack",
        "پانیک": "panic_attack",
        # student / users
        "student ha": "دانشجوها",
        "student-ha": "دانشجوها",
        "students": "دانشجوها",
        "student": "دانشجو",
        "بچه‌ها": "دانشجوها",
        "بچه ها": "دانشجوها",
        "دانشجوها": "دانشجوها",
        # metrics
        "cgpa": "cgpa",
        "gpa": "cgpa",
        "grade": "نمره",
        "exam score": "نمره امتحان",
        "mental health": "سلامت روان",
        "risk": "ریسک",
        "high risk": "ریسک بالا",
        # colloquial actions
        "چندتا": "تعداد",
        "چند تا": "تعداد",
        "چنده": "چقدر است",
        "چقدره": "چقدر است",
        "چند درصده": "درصد",
        "chand darsade": "درصد",
        "average": "میانگین",
        "avg": "میانگین",
        "rate": "نرخ",
        "دارن": "دارند",
        "ندارن": "ندارند",
        "نداره": "ندارد",
        "بده": "نمایش بده",
        "نشون بده": "نمایش بده",
        "نشان بده": "نمایش بده",
    }

    PHRASE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
        (re.compile(r"\bstudent\s*ha\b", re.IGNORECASE), "دانشجوها"),
        (re.compile(r"\bchand\s*darsad(e|eh)?\b", re.IGNORECASE), "چند درصد"),
        (re.compile(r"\baverage\s+chand(e|eh)?\b", re.IGNORECASE), "میانگین چقدر است"),
    ]

    def normalize(self, text: str) -> ColloquialMappingResult:
        normalized = text
        matched: dict[str, str] = {}

        for pattern, replacement in self.PHRASE_PATTERNS:
            if pattern.search(normalized):
                matched[pattern.pattern] = replacement
                normalized = pattern.sub(replacement, normalized)

        for src, dst in sorted(self.TERM_MAP.items(), key=lambda x: len(x[0]), reverse=True):
            pattern = re.compile(rf"(?<!\w){re.escape(src)}(?!\w)", re.IGNORECASE)
            if pattern.search(normalized):
                matched[src] = dst
                normalized = pattern.sub(dst, normalized)

        normalized = re.sub(r"\s+", " ", normalized).strip()
        return ColloquialMappingResult(text, normalized, matched)

    def expand_terms(self, text: str) -> list[str]:
        result = self.normalize(text)
        terms = set(result.normalized.split())
        terms.update(result.matched_terms.values())
        return sorted(t for t in terms if t)
