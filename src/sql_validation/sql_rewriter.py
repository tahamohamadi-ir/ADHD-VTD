from __future__ import annotations

import re


class SQLRewriter:
    """Small deterministic rewrites. Never turns unsafe SQL into safe SQL; validators run separately.

    Capabilities:
    - Strip trailing semicolons
    - Strip markdown code fences (```sql ... ```)
    - Ensure LIMIT for raw SELECT queries
    - Normalize whitespace
    - Fix common column name typos (gpa → cgpa)
    """

    AGG_RE = re.compile(r"\b(count|avg|sum|min|max|round)\s*\(", re.IGNORECASE)
    FENCE_RE = re.compile(r"^```(?:sql|sqlite)?\s*\n?(.*?)\n?```$", re.DOTALL | re.IGNORECASE)

    # Common column name fixes
    COLUMN_FIXES: dict[str, str] = {
        r"\bgpa\b": "cgpa",  # The schema uses cgpa_10 / cgpa_mid, not gpa
    }

    def strip_markdown_fences(self, sql: str) -> str:
        """Remove markdown code fences wrapping SQL.

        Handles:
        - ```sql\\nSELECT ...\\n```
        - ```\\nSELECT ...\\n```
        - ``` SELECT ... ```
        """
        s = (sql or "").strip()
        match = self.FENCE_RE.match(s)
        if match:
            return match.group(1).strip()
        # Also handle inline backticks
        if s.startswith("`") and s.endswith("`") and not s.startswith("```"):
            return s.strip("`").strip()
        return s

    def strip_trailing_semicolon(self, sql: str) -> str:
        return (sql or "").strip().rstrip(";").strip()

    def fix_column_names(self, sql: str) -> str:
        """Fix common column name typos in SQL.

        Currently handles:
        - gpa → cgpa (when used as a standalone column reference, not part of cgpa)
        """
        s = sql
        for pattern, replacement in self.COLUMN_FIXES.items():
            # Only replace 'gpa' when it's NOT already part of 'cgpa'
            s = re.sub(r"(?<!c)" + pattern, replacement, s, flags=re.IGNORECASE)
        return s

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

    def rewrite(self, sql: str, *, add_limit: bool = True, limit: int = 100) -> str:
        """Apply all rewrites in sequence.

        Order:
        1. Strip markdown fences
        2. Strip trailing semicolons
        3. Fix column name typos
        4. Add LIMIT if needed
        5. Normalize whitespace
        """
        s = self.strip_markdown_fences(sql)
        s = self.strip_trailing_semicolon(s)
        s = self.fix_column_names(s)
        if add_limit:
            s = self.ensure_limit_for_raw_select(s, limit=limit)
        s = self.normalize(s)
        return s
