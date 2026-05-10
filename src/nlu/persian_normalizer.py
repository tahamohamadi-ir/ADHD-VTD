from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

try:
    from src.nlu.number_normalizer import NumberNormalizer
    from src.nlu.colloquial_mapper import ColloquialMapper
except Exception:  # pragma: no cover
    from number_normalizer import NumberNormalizer
    from colloquial_mapper import ColloquialMapper

@dataclass(frozen=True)
class PersianNormalizationResult:
    original: str
    normalized: str
    matched_colloquials: dict[str, str] = field(default_factory=dict)

class PersianNormalizer:
    """Persian + mixed Persian/English normalizer for VTD queries."""

    ARABIC_TO_PERSIAN = str.maketrans({
        "ك": "ک", "ي": "ی", "ى": "ی", "ة": "ه", "ۀ": "ه", "ؤ": "و", "إ": "ا", "أ": "ا", "ٱ": "ا",
    })
    DIACRITICS_RE = re.compile(r"[\u064B-\u065F\u0670]")
    PUNCT_TRANSLATION = str.maketrans({
        "؟": "?", "،": ",", "؛": ";", "٪": "%", "٫": ".", "٬": ",",
        "“": '"', "”": '"', "‘": "'", "’": "'",
    })

    TYPO_FIXES: dict[str, str] = {
        "افسوردگی": "افسردگی",
        "اضتراب": "اضطراب",
        "فشار تحصیلیه": "فشار تحصیلی",
        "سوشال مدیا": "شبکه اجتماعی",
    }

    def __init__(self, enable_colloquial_mapping: bool = True) -> None:
        self.number_normalizer = NumberNormalizer()
        self.colloquial_mapper = ColloquialMapper()
        self.enable_colloquial_mapping = enable_colloquial_mapping

    def normalize_chars(self, text: str) -> str:
        text = unicodedata.normalize("NFKC", text or "")
        text = text.translate(self.ARABIC_TO_PERSIAN)
        text = self.DIACRITICS_RE.sub("", text)
        text = text.translate(self.PUNCT_TRANSLATION)
        text = re.sub(r"\u200c+", " ", text)
        text = re.sub(r"[\t\r\n]+", " ", text)
        return text

    def normalize_spacing(self, text: str) -> str:
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"\s+([?,.;:%])", r"\1", text)
        return text.strip()

    def apply_typo_fixes(self, text: str) -> str:
        out = text
        for src, dst in sorted(self.TYPO_FIXES.items(), key=lambda x: len(x[0]), reverse=True):
            out = re.sub(re.escape(src), dst, out, flags=re.IGNORECASE)
        return out

    def normalize_text(self, text: str) -> str:
        return self.normalize(text).normalized

    def normalize(self, text: str) -> PersianNormalizationResult:
        original = text or ""
        normalized = self.normalize_chars(original)
        normalized = self.number_normalizer.normalize_digits(normalized)
        normalized = self.apply_typo_fixes(normalized)
        matched: dict[str, str] = {}
        if self.enable_colloquial_mapping:
            mapped = self.colloquial_mapper.normalize(normalized)
            normalized = mapped.normalized
            matched = mapped.matched_terms
        normalized = self.normalize_spacing(normalized)
        return PersianNormalizationResult(original, normalized, matched)


def normalize_persian(text: str) -> str:
    return PersianNormalizer().normalize_text(text)
