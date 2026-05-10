from __future__ import annotations

import re
from dataclasses import dataclass, field

try:
    from src.nlu.persian_normalizer import PersianNormalizer
except Exception:  # pragma: no cover
    from persian_normalizer import PersianNormalizer

@dataclass(frozen=True)
class SafetyDecision:
    is_safe: bool
    label: str
    reasons: list[str] = field(default_factory=list)
    matched_patterns: list[str] = field(default_factory=list)

class SafetyIntentDetector:
    """Rule-based safety gate before any SQL generation."""

    FORBIDDEN_SQL = [
        "insert", "update", "delete", "drop", "alter", "create", "truncate", "replace", "merge",
        "attach", "detach", "pragma", "vacuum", "reindex", "exec", "execute", "call",
    ]
    PERSIAN_DANGEROUS = [
        "حذف کن", "پاک کن", "دیتابیس را پاک", "جدول را پاک", "آپدیت کن", "ویرایش کن",
        "تغییر بده", "بساز", "ساخت جدول", "همه داده ها را بده", "همه اطلاعات افراد",
    ]
    PROMPT_INJECTION = [
        "ignore previous", "ignore all", "system prompt", "developer message", "jailbreak",
        "دستور قبلی را نادیده", "قوانین را نادیده", "پرامپت سیستم", "پیام سیستم",
    ]

    def __init__(self) -> None:
        self.normalizer = PersianNormalizer()

    def detect(self, text: str) -> SafetyDecision:
        norm = self.normalizer.normalize_text(text).lower()
        reasons: list[str] = []
        matched: list[str] = []

        for keyword in self.FORBIDDEN_SQL:
            if re.search(rf"\b{re.escape(keyword)}\b", norm):
                matched.append(keyword)
                reasons.append(f"Forbidden SQL operation requested: {keyword}")

        for phrase in self.PERSIAN_DANGEROUS:
            if phrase in norm:
                matched.append(phrase)
                reasons.append(f"Dangerous Persian operation phrase: {phrase}")

        for phrase in self.PROMPT_INJECTION:
            if phrase in norm:
                matched.append(phrase)
                reasons.append(f"Prompt-injection phrase: {phrase}")

        if ";" in norm and re.search(r"\b(select|drop|delete|update|insert|pragma)\b", norm):
            matched.append("multi_statement_like")
            reasons.append("Multiple-statement or SQL-injection-like text detected.")

        if reasons:
            label = "prompt_injection" if any("Prompt" in r for r in reasons) else "unsafe_sql"
            return SafetyDecision(False, label, reasons, matched)
        return SafetyDecision(True, "safe", [], [])

    def is_safe(self, text: str) -> bool:
        return self.detect(text).is_safe
