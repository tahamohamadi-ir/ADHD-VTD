from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Protocol

import sqlglot

_SQLITE_DIALECT = "sqlite"

_CODE_FENCE_PATTERN = re.compile(
    r"^\s*```(?:sql)?[ \t]*\r?\n(?P<body>.*?)\r?\n?[ \t]*```\s*$",
    re.DOTALL | re.IGNORECASE,
)
_TRAILING_SEMICOLON_PATTERN = re.compile(r";[;\s]*$")


@dataclass(frozen=True)
class SurgeonOutcome:
    original: str
    repaired: str
    applied: tuple[str, ...]
    confidences: tuple[float, ...]


class RepairStrategy(Protocol):
    name: str
    confidence: float

    def apply(self, sql: str) -> str | None: ...


class StripCodeFenceStrategy:
    name = "strip_code_fence"
    confidence = 0.9

    def apply(self, sql: str) -> str | None:
        match = _CODE_FENCE_PATTERN.match(sql)
        if match is None:
            return None
        body = match.group("body").strip()
        return body or None


class TrailingSemicolonStrategy:
    name = "trailing_semicolon"
    confidence = 0.99

    def apply(self, sql: str) -> str | None:
        if not _TRAILING_SEMICOLON_PATTERN.search(sql):
            return None
        stripped = _TRAILING_SEMICOLON_PATTERN.sub("", sql, count=1).rstrip()
        return stripped or None


class BalancedQuoteFixStrategy:
    name = "balanced_quote_fix"
    confidence = 0.55

    def apply(self, sql: str) -> str | None:
        if sql.count("'") % 2 == 0 or _parses(sql):
            return None
        candidate = f"{sql.rstrip()}'"
        return None if candidate == sql else candidate


_STRATEGIES: tuple[RepairStrategy, ...] = (
    StripCodeFenceStrategy(),
    TrailingSemicolonStrategy(),
    BalancedQuoteFixStrategy(),
)


def apply_surgeon(sql: str, *, max_rounds: int = 2) -> SurgeonOutcome:
    """Apply deterministic syntax-only repairs.

    A patch is accepted only when the patched SQL parses under the sqlite dialect;
    an already-parseable statement is never turned into an unparseable one.
    """
    original = sql or ""
    current = original
    applied: list[str] = []
    confidences: list[float] = []
    for _ in range(max(0, max_rounds)):
        step = _first_accepted(current)
        if step is None:
            break
        strategy, candidate = step
        applied.append(strategy.name)
        confidences.append(strategy.confidence)
        current = candidate
    return SurgeonOutcome(original, current, tuple(applied), tuple(confidences))


def _first_accepted(sql: str) -> tuple[RepairStrategy, str] | None:
    for strategy in _STRATEGIES:
        candidate = strategy.apply(sql)
        if candidate is None or candidate == sql:
            continue
        if _parses(candidate):
            return strategy, candidate
    return None


def _parses(sql: str) -> bool:
    try:
        sqlglot.parse_one(sql, read=_SQLITE_DIALECT)
    except Exception:
        return False
    return True
