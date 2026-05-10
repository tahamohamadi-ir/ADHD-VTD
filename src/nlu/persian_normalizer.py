from __future__ import annotations

import re
import unicodedata

from src.core.types import NormalizationResult


class PersianNormalizer:
    """
    Persian-first text normalizer for Text-to-SQL.

    Responsibilities:
    - Arabic/Persian character unification
    - ZWNJ handling
    - Arabic/Persian digit normalization is delegated to NumberNormalizer
    - Basic punctuation and whitespace cleanup
    """

    ARABIC_TO_PERSIAN = str.maketrans(
        {
            "ك": "ک",
            "ي": "ی",
            "ى": "ی",
            "ۀ": "ه",
            "ة": "ه",
            "ؤ": "و",
            "إ": "ا",
            "أ": "ا",
            "آ": "آ",
        }
    )

    DIACRITICS_PATTERN = re.compile(r"[\u064B-\u065F\u0670\u06D6-\u06ED]")
    ZWNJ_PATTERN = re.compile(r"[\u200c\u200d]")
    MULTISPACE_PATTERN = re.compile(r"\s+")

    PUNCT_TRANSLATION = str.maketrans(
        {
            "؟": "?",
            "،": ",",
            "؛": ";",
            "٬": ",",
            "٫": ".",
            "“": '"',
            "”": '"',
            "’": "'",
        }
    )

    def __init__(self, replace_zwnj_with_space: bool = True) -> None:
        self.replace_zwnj_with_space = replace_zwnj_with_space

    def normalize(self, text: str) -> NormalizationResult:
        raw = text or ""
        normalized = self.normalize_text(raw)
        notes: list[str] = []

        if raw != normalized:
            notes.append("Persian text normalized.")

        return NormalizationResult(
            raw_text=raw,
            normalized_text=normalized,
            detected_date_ranges=[],
            notes=notes,
        )

    def normalize_text(self, text: str) -> str:
        if not text:
            return ""

        text = unicodedata.normalize("NFKC", text)
        text = text.translate(self.ARABIC_TO_PERSIAN)
        text = text.translate(self.PUNCT_TRANSLATION)
        text = self.DIACRITICS_PATTERN.sub("", text)

        if self.replace_zwnj_with_space:
            text = self.ZWNJ_PATTERN.sub(" ", text)
        else:
            text = self.ZWNJ_PATTERN.sub("\u200c", text)

        text = self.MULTISPACE_PATTERN.sub(" ", text)
        return text.strip()

    def normalize_for_search(self, text: str) -> str:
        text = self.normalize_text(text).lower()
        text = re.sub(r"[^\w\s\-.]", " ", text, flags=re.UNICODE)
        text = self.MULTISPACE_PATTERN.sub(" ", text)
        return text.strip()


def normalize_persian(text: str) -> str:
    return PersianNormalizer().normalize_text(text)
