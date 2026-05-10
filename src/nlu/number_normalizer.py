from __future__ import annotations

import re


class NumberNormalizer:
    """
    Converts Persian and Arabic digits into Western digits.

    This component intentionally keeps complex Persian number-word parsing minimal.
    """

    DIGIT_MAP = str.maketrans(
        {
            "۰": "0",
            "۱": "1",
            "۲": "2",
            "۳": "3",
            "۴": "4",
            "۵": "5",
            "۶": "6",
            "۷": "7",
            "۸": "8",
            "۹": "9",
            "٠": "0",
            "١": "1",
            "٢": "2",
            "٣": "3",
            "٤": "4",
            "٥": "5",
            "٦": "6",
            "٧": "7",
            "٨": "8",
            "٩": "9",
        }
    )

    SIMPLE_WORD_NUMBERS = {
        "صفر": 0,
        "یک": 1,
        "یه": 1,
        "دو": 2,
        "سه": 3,
        "چهار": 4,
        "پنج": 5,
        "شش": 6,
        "شیش": 6,
        "هفت": 7,
        "هشت": 8,
        "نه": 9,
        "ده": 10,
        "یازده": 11,
        "دوازده": 12,
        "سیزده": 13,
        "چهارده": 14,
        "پانزده": 15,
        "شانزده": 16,
        "هفده": 17,
        "هجده": 18,
        "نوزده": 19,
        "بیست": 20,
    }

    NUMBER_PATTERN = re.compile(r"[-+]?\d+(?:\.\d+)?")

    def normalize_digits(self, text: str) -> str:
        if not text:
            return ""
        return text.translate(self.DIGIT_MAP)

    def replace_simple_number_words(self, text: str) -> str:
        if not text:
            return ""

        result = text
        for word, number in sorted(self.SIMPLE_WORD_NUMBERS.items(), key=lambda x: len(x[0]), reverse=True):
            result = re.sub(rf"\b{re.escape(word)}\b", str(number), result)
        return result

    def normalize(self, text: str, replace_words: bool = False) -> str:
        text = self.normalize_digits(text)
        if replace_words:
            text = self.replace_simple_number_words(text)
        return text

    def extract_numbers(self, text: str) -> list[float]:
        text = self.normalize_digits(text)
        values: list[float] = []

        for match in self.NUMBER_PATTERN.findall(text):
            if "." in match:
                values.append(float(match))
            else:
                values.append(float(int(match)))

        return values


def normalize_digits(text: str) -> str:
    return NumberNormalizer().normalize_digits(text)
