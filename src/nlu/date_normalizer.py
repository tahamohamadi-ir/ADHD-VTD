from __future__ import annotations

import calendar
import re
from datetime import date, timedelta

from src.core.types import DateRange
from src.nlu.number_normalizer import NumberNormalizer
from src.nlu.persian_normalizer import PersianNormalizer

try:
    from persiantools.jdatetime import JalaliDate
except Exception:  # pragma: no cover
    JalaliDate = None


class PersianDateNormalizer:
    """
    Converts common Persian/Jalali date expressions into Gregorian ISO ranges.

    Supported examples:
    - 1404/01/15
    - ۱۴۰۴-۰۱-۱۵
    - فروردین ۱۴۰۴
    - سال ۱۴۰۴
    """

    MONTHS = {
        "فروردین": 1,
        "اردیبهشت": 2,
        "خرداد": 3,
        "تیر": 4,
        "مرداد": 5,
        "شهریور": 6,
        "مهر": 7,
        "آبان": 8,
        "اذر": 9,
        "آذر": 9,
        "دی": 10,
        "بهمن": 11,
        "اسفند": 12,
    }

    DATE_PATTERN = re.compile(r"(?P<year>13\d{2}|14\d{2})[/-](?P<month>\d{1,2})[/-](?P<day>\d{1,2})")
    MONTH_YEAR_PATTERN = re.compile(r"(?P<month_name>فروردین|اردیبهشت|خرداد|تیر|مرداد|شهریور|مهر|آبان|اذر|آذر|دی|بهمن|اسفند)\s+(?P<year>13\d{2}|14\d{2})")
    YEAR_PATTERN = re.compile(r"(?:سال\s+)?(?P<year>13\d{2}|14\d{2})")

    def __init__(self) -> None:
        self.persian_normalizer = PersianNormalizer()
        self.number_normalizer = NumberNormalizer()

    def normalize_text_dates(self, text: str) -> tuple[str, list[DateRange]]:
        normalized = self.persian_normalizer.normalize_text(text)
        normalized = self.number_normalizer.normalize_digits(normalized)

        ranges: list[DateRange] = []

        for match in self.DATE_PATTERN.finditer(normalized):
            year = int(match.group("year"))
            month = int(match.group("month"))
            day = int(match.group("day"))
            start = self.jalali_to_gregorian(year, month, day)
            end = start + timedelta(days=1)
            ranges.append(
                DateRange(
                    original_text=match.group(0),
                    start_date=start.isoformat(),
                    end_date=end.isoformat(),
                    calendar="jalali",
                    granularity="day",
                )
            )

        for match in self.MONTH_YEAR_PATTERN.finditer(normalized):
            month_name = match.group("month_name")
            year = int(match.group("year"))
            month = self.MONTHS[month_name]
            start = self.jalali_to_gregorian(year, month, 1)

            if month == 12:
                next_year, next_month = year + 1, 1
            else:
                next_year, next_month = year, month + 1

            end = self.jalali_to_gregorian(next_year, next_month, 1)
            ranges.append(
                DateRange(
                    original_text=match.group(0),
                    start_date=start.isoformat(),
                    end_date=end.isoformat(),
                    calendar="jalali",
                    granularity="month",
                )
            )

        return normalized, ranges

    def jalali_to_gregorian(self, year: int, month: int, day: int) -> date:
        if JalaliDate is None:
            raise RuntimeError("persiantools is required for Jalali date conversion.")
        return JalaliDate(year, month, day).to_gregorian()

    def gregorian_month_range(self, year: int, month: int) -> tuple[date, date]:
        last_day = calendar.monthrange(year, month)[1]
        start = date(year, month, 1)
        end = date(year, month, last_day) + timedelta(days=1)
        return start, end


def normalize_persian_dates(text: str) -> tuple[str, list[DateRange]]:
    return PersianDateNormalizer().normalize_text_dates(text)
