"""Term extractor for VTD NLU pipeline.

Extracts semantic anchor tokens from a normalized Persian question.
These tokens are used as input to the schema linker and value linker
for matching against schema aliases, glossary terms, and metric definitions.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from src.nlu.persian_normalizer import PersianNormalizer


# Common Persian stopwords that carry no schema-linking signal
PERSIAN_STOPWORDS: set[str] = {
    "و",
    "در",
    "به",
    "از",
    "که",
    "این",
    "را",
    "با",
    "آن",
    "یک",
    "یه",
    "برای",
    "تا",
    "هم",
    "است",
    "بود",
    "شد",
    "می",
    "هر",
    "اگر",
    "یا",
    "ها",
    "های",
    "ای",
    "آیا",
    "چه",
    "اما",
    "ولی",
    "بین",
    "همه",
    "هست",
    "نیست",
    "باشد",
    "شود",
    "شده",
    "بر",
    "روی",
    "کنید",
    "کنم",
    "لطفا",
    "لطفاً",
    "بده",
    "بگو",
    "نشون",
    "نشان",
    "نمایش",
    "مقدار",
    "مقداری",
    "چند",
    "چندتا",
    "چنده",
    "تعدادی",
    "خیلی",
    "خوب",
    "بد",
    "کمی",
}

# English stopwords commonly appearing in mixed queries
ENGLISH_STOPWORDS: set[str] = {
    "the",
    "a",
    "an",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "being",
    "of",
    "in",
    "for",
    "to",
    "and",
    "or",
    "not",
    "it",
    "its",
    "this",
    "that",
    "what",
    "how",
    "many",
    "much",
    "which",
    "who",
    "where",
    "show",
    "me",
    "give",
    "get",
    "tell",
    "list",
    "find",
    "all",
    "each",
    "by",
    "on",
    "at",
    "with",
    "from",
}


@dataclass(frozen=True)
class TermExtractionResult:
    """Result of term extraction from a query."""

    original: str
    normalized: str
    terms: list[str] = field(default_factory=list)
    bigrams: list[str] = field(default_factory=list)
    trigrams: list[str] = field(default_factory=list)
    numbers: list[str] = field(default_factory=list)


class TermExtractor:
    """Extract semantic anchor tokens from a normalized Persian question.

    The extractor produces:
    - Unigrams (individual tokens minus stopwords)
    - Bigrams (adjacent pairs for compound terms like "ریسک بالا")
    - Trigrams (adjacent triples for phrases like "سلامت روان دانشجوها")
    - Numbers (numeric tokens for potential filter values)
    """

    def __init__(self, extra_stopwords: set[str] | None = None) -> None:
        self.normalizer = PersianNormalizer()
        import hazm

        self.tokenizer = hazm.WordTokenizer()
        self.stopwords = PERSIAN_STOPWORDS | ENGLISH_STOPWORDS
        if extra_stopwords:
            self.stopwords = self.stopwords | extra_stopwords

    def _tokenize(self, text: str) -> list[str]:
        """Split text into tokens using hazm tokenizer, preserving valid words."""
        tokens = self.tokenizer.tokenize(text.lower())
        # Filter out pure punctuation tokens
        return [t for t in tokens if re.match(r"[\w\u0600-\u06FF]+", t)]

    def _is_stopword(self, token: str) -> bool:
        return token in self.stopwords

    def _extract_numbers(self, tokens: list[str]) -> list[str]:
        return [t for t in tokens if re.match(r"^\d+(\.\d+)?$", t)]

    def extract(self, text: str) -> TermExtractionResult:
        """Extract terms from the input text.

        Args:
            text: Raw user question (will be normalized internally).

        Returns:
            TermExtractionResult with unigrams, bigrams, trigrams, and numbers.
        """
        original = text or ""
        normalized = self.normalizer.normalize_text(original)
        all_tokens = self._tokenize(normalized)

        # Extract numbers before filtering
        numbers = self._extract_numbers(all_tokens)

        # Filter stopwords for semantic tokens
        semantic_tokens = [
            t for t in all_tokens if not self._is_stopword(t) and not re.match(r"^\d+$", t)
        ]

        # Build n-grams from the full (non-stopword-filtered) token list
        # for catching compound terms
        content_tokens = [t for t in all_tokens if not self._is_stopword(t)]
        bigrams = [
            f"{content_tokens[i]} {content_tokens[i + 1]}" for i in range(len(content_tokens) - 1)
        ]
        trigrams = [
            f"{content_tokens[i]} {content_tokens[i + 1]} {content_tokens[i + 2]}"
            for i in range(len(content_tokens) - 2)
        ]

        return TermExtractionResult(
            original=original,
            normalized=normalized,
            terms=semantic_tokens,
            bigrams=bigrams,
            trigrams=trigrams,
            numbers=numbers,
        )

    def extract_terms(self, text: str) -> list[str]:
        """Convenience method: return just the list of semantic terms."""
        result = self.extract(text)
        return result.terms

    def extract_all_ngrams(self, text: str) -> list[str]:
        """Return unigrams + bigrams + trigrams combined (deduplicated, ordered)."""
        result = self.extract(text)
        seen: set[str] = set()
        combined: list[str] = []
        # Prioritize longer n-grams first (they're more specific)
        for ngram in result.trigrams + result.bigrams + result.terms:
            if ngram not in seen:
                seen.add(ngram)
                combined.append(ngram)
        return combined
