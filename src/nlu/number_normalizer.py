from __future__ import annotations

import re
from dataclasses import dataclass

PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹"
ARABIC_DIGITS = "٠١٢٣٤٥٦٧٨٩"
ENGLISH_DIGITS = "0123456789"
DIGIT_TRANSLATION = str.maketrans(
    {**{p: e for p, e in zip(PERSIAN_DIGITS, ENGLISH_DIGITS)},
     **{a: e for a, e in zip(ARABIC_DIGITS, ENGLISH_DIGITS)}}
)


# Important: colloquial "یه" is intentionally NOT mapped to 1.
# In Persian user questions it often means an indefinite article, e.g. "یه آمار کلی بده".
# Mapping it to 1 would create false numeric filters/signals.
PERSIAN_NUMBER_WORDS: dict[str, int] = {
    "صفر": 0, "یک": 1, "دو": 2, "سه": 3, "چهار": 4, "پنج": 5,
    "شش": 6, "هفت": 7, "هشت": 8, "نه": 9, "ده": 10, "یازده": 11, "دوازده": 12,
    "سیزده": 13, "چهارده": 14, "پانزده": 15, "شانزده": 16, "هفده": 17,
    "هجده": 18, "نوزده": 19, "بیست": 20, "سی": 30, "چهل": 40, "پنجاه": 50,
    "شصت": 60, "هفتاد": 70, "هشتاد": 80, "نود": 90, "صد": 100,
}

@dataclass(frozen=True)
class NumberNormalizationResult:
    original: str
    normalized: str
    extracted_numbers: list[float]

class NumberNormalizer:
    """Normalize Persian/Arabic digits and extract simple numeric signals."""

    def normalize_digits(self, text: str) -> str:
        return text.translate(DIGIT_TRANSLATION)

    def normalize_number_words(self, text: str) -> str:
        out = text
        for word, value in sorted(PERSIAN_NUMBER_WORDS.items(), key=lambda x: len(x[0]), reverse=True):
            out = re.sub(rf"(?<!\w){re.escape(word)}(?!\w)", str(value), out)
        return out

    def extract_numbers(self, text: str) -> list[float]:
        normalized = self.normalize_digits(text)
        values: list[float] = []
        for match in re.findall(r"[-+]?\d+(?:\.\d+)?", normalized):
            try:
                values.append(float(match) if "." in match else int(match))
            except ValueError:
                continue
        return values

    def normalize(self, text: str) -> NumberNormalizationResult:
        normalized = self.normalize_digits(text)
        normalized = self.normalize_number_words(normalized)
        return NumberNormalizationResult(
            original=text,
            normalized=normalized,
            extracted_numbers=self.extract_numbers(normalized),
        )


def normalize_digits(text: str) -> str:
    return NumberNormalizer().normalize_digits(text)
