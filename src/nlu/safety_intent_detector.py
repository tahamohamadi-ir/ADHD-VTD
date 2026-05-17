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
        "insert",
        "update",
        "delete",
        "drop",
        "alter",
        "create",
        "truncate",
        "replace",
        "merge",
        "attach",
        "detach",
        "pragma",
        "vacuum",
        "reindex",
        "exec",
        "execute",
        "call",
    ]
    PERSIAN_DANGEROUS = [
        "\u062d\u0630\u0641 \u06a9\u0646",
        "\u067e\u0627\u06a9 \u06a9\u0646",
        "\u062f\u06cc\u062a\u0627\u0628\u06cc\u0633 \u0631\u0627 \u067e\u0627\u06a9",
        "\u062c\u062f\u0648\u0644 \u0631\u0627 \u067e\u0627\u06a9",
        "\u0622\u067e\u062f\u06cc\u062a \u06a9\u0646",
        "\u0648\u06cc\u0631\u0627\u06cc\u0634 \u06a9\u0646",
        "\u062a\u063a\u06cc\u06cc\u0631 \u0628\u062f\u0647",
        "\u0633\u0627\u062e\u062a \u062c\u062f\u0648\u0644",
        "\u0647\u0645\u0647 \u062f\u0627\u062f\u0647 \u0647\u0627 \u0631\u0627 \u0628\u062f\u0647",
        "\u0647\u0645\u0647 \u0627\u0637\u0644\u0627\u0639\u0627\u062a \u0627\u0641\u0631\u0627\u062f",
    ]
    PERSIAN_DESTRUCTIVE_CREATE_CONTEXTS = [
        "\u062c\u062f\u0648\u0644 \u0628\u0633\u0627\u0632",
        "\u062f\u06cc\u062a\u0627\u0628\u06cc\u0633 \u0628\u0633\u0627\u0632",
        "\u0633\u0627\u062e\u062a \u062c\u062f\u0648\u0644",
        "\u0633\u0627\u062e\u062a \u062f\u06cc\u062a\u0627\u0628\u06cc\u0633",
    ]
    PROMPT_INJECTION = [
        "ignore previous",
        "ignore all",
        "system prompt",
        "developer message",
        "jailbreak",
        "\u062f\u0633\u062a\u0648\u0631 \u0642\u0628\u0644\u06cc \u0631\u0627 \u0646\u0627\u062f\u06cc\u062f\u0647",
        "\u0642\u0648\u0627\u0646\u06cc\u0646 \u0631\u0627 \u0646\u0627\u062f\u06cc\u062f\u0647",
        "\u067e\u0631\u0627\u0645\u067e\u062a \u0633\u06cc\u0633\u062a\u0645",
        "\u067e\u06cc\u0627\u0645 \u0633\u06cc\u0633\u062a\u0645",
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

        for phrase in self.PERSIAN_DESTRUCTIVE_CREATE_CONTEXTS:
            if phrase in norm:
                matched.append(phrase)
                reasons.append(f"Dangerous Persian create operation phrase: {phrase}")

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
