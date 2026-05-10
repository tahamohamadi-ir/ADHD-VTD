from __future__ import annotations

import re

class SQLRewriter:
    """Small deterministic rewrites. Never turns unsafe SQL into safe SQL; validators run separately."""

    AGG_RE = re.compile(r"\b(count|avg|sum|min|max|round)\s*\(", re.IGNORECASE)

    def strip_trailing_semicolon(self, sql: str) -> str:
        return (sql or "").strip().rstrip(";").strip()

    def ensure_limit_for_raw_select(self, sql: str, limit: int = 100) -> str:
        s = self.strip_trailing_semicolon(sql)
        lower = s.lower()
        if " limit " in lower:
            return s
        if self.AGG_RE.search(s) or " group by " in lower:
            return s
        if lower.startswith("select") or lower.startswith("with"):
            return f"{s} LIMIT {int(limit)}"
        return s

    def normalize(self, sql: str) -> str:
        return re.sub(r"\s+", " ", self.strip_trailing_semicolon(sql)).strip()
