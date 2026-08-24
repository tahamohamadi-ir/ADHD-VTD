from __future__ import annotations

import re
from dataclasses import dataclass

try:
    import jdatetime  # type: ignore
except Exception:  # pragma: no cover
    jdatetime = None

try:
    from src.nlu.number_normalizer import NumberNormalizer
except Exception:  # pragma: no cover
    from number_normalizer import NumberNormalizer

JALALI_MONTHS = {
    "فروردین": 1,
    "اردیبهشت": 2,
    "خرداد": 3,
    "تیر": 4,
    "مرداد": 5,
    "شهریور": 6,
    "مهر": 7,
    "آبان": 8,
    "ابان": 8,
    "آذر": 9,
    "اذر": 9,
    "دی": 10,
    "بهمن": 11,
    "اسفند": 12,
}


@dataclass(frozen=True)
class DateNormalizationResult:
    original: str
    normalized_text: str
    has_temporal_expression: bool
    needs_clarification: bool
    reason: str | None = None
    date_range: dict[str, str] | None = None


class PersianDateNormalizer:
    """Resolve explicit Jalali month/year if possible; otherwise request clarification."""

    def __init__(self) -> None:
        self.number_normalizer = NumberNormalizer()

    def _jalali_month_range(self, jy: int, jm: int) -> dict[str, str] | None:
        if jdatetime is None:
            return None
        start_j = jdatetime.date(jy, jm, 1)
        if jm == 12:
            end_j = jdatetime.date(jy + 1, 1, 1)
        else:
            end_j = jdatetime.date(jy, jm + 1, 1)
        start_g = start_j.togregorian()
        end_g = end_j.togregorian()
        return {
            "start": start_g.isoformat(),
            "end_exclusive": end_g.isoformat(),
            "calendar": "jalali_to_gregorian",
        }

    def normalize(
        self, text: str, target_date_column: str | None = None
    ) -> DateNormalizationResult:
        original = text or ""
        normalized = self.number_normalizer.normalize_digits(original)

        has_temporal = any(m in normalized for m in JALALI_MONTHS) or bool(
            re.search(r"\b1[34]\d{2}\b", normalized)
        )
        has_temporal = has_temporal or any(
            x in normalized
            for x in [
                "امسال",
                "پارسال",
                "سال قبل",
                "ماه قبل",
                "آخرین سال",
                "latest",
                "last year",
            ]
        )
        if not has_temporal:
            return DateNormalizationResult(original, normalized, False, False)

        if not target_date_column and any(
            x in normalized
            for x in [
                "امسال",
                "پارسال",
                "ماه",
                "سال",
                "آخرین سال",
                "latest",
                "last year",
            ]
        ):
            return DateNormalizationResult(
                original,
                normalized,
                True,
                True,
                "Temporal expression detected but target date/year column is not fixed yet.",
            )

        # Explicit Jalali month + year e.g. فروردین 1404
        for month_name, month_no in JALALI_MONTHS.items():
            if month_name in normalized:
                m = re.search(r"\b(13\d{2}|14\d{2})\b", normalized)
                if not m:
                    return DateNormalizationResult(
                        original,
                        normalized,
                        True,
                        True,
                        "Jalali month found without explicit year.",
                    )
                jy = int(m.group(1))
                rng = self._jalali_month_range(jy, month_no)
                if rng is None:
                    return DateNormalizationResult(
                        original,
                        normalized,
                        True,
                        True,
                        "jdatetime is not installed; cannot safely convert Jalali date.",
                    )
                return DateNormalizationResult(original, normalized, True, False, None, rng)

        return DateNormalizationResult(
            original,
            normalized,
            True,
            True,
            "Temporal expression requires schema-specific interpretation before SQL generation.",
        )
