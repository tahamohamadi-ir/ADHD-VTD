from __future__ import annotations

import re
import sqlglot
from sqlglot import exp

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
        "gpa": "cgpa",  # The schema uses cgpa_10 / cgpa_mid, not gpa
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

    def fix_column_names_ast(self, tree: exp.Expression) -> exp.Expression:
        """Fix common column name typos in SQL using AST."""
        for col in tree.find_all(exp.Column):
            if col.name.lower() in self.COLUMN_FIXES:
                # Replace with correct name
                col.set("this", exp.Identifier(this=self.COLUMN_FIXES[col.name.lower()], quoted=col.this.args.get("quoted")))
        return tree

    def ensure_limit_ast(self, tree: exp.Expression, limit: int = 100) -> exp.Expression:
        """Ensure LIMIT is present for raw SELECT queries using AST."""
        if not isinstance(tree, exp.Select):
            return tree
            
        # If there's already a limit, do nothing
        if tree.args.get("limit"):
            return tree
            
        # If there's a GROUP BY, do nothing
        if tree.args.get("group"):
            return tree
            
        # If there's an aggregate function, do nothing
        has_agg = False
        for node in tree.walk():
            if isinstance(node, (exp.Count, exp.Avg, exp.Sum, exp.Min, exp.Max)):
                has_agg = True
                break
                
        if not has_agg:
            tree = tree.limit(limit)
            
        return tree

    def rewrite(self, sql: str, *, add_limit: bool = True, limit: int = 100) -> str:
        """Apply all rewrites in sequence.

        Order:
        1. Strip markdown fences and trailing semicolons (string level)
        2. Parse with sqlglot
        3. Fix column name typos (AST level)
        4. Add LIMIT if needed (AST level)
        5. Serialize back to SQL string
        """
        s = self.strip_markdown_fences(sql)
        s = self.strip_trailing_semicolon(s)
        
        try:
            import sqlglot
            from sqlglot import exp
            
            tree = sqlglot.parse_one(s, read="sqlite")
            tree = self.fix_column_names_ast(tree)
            
            if add_limit:
                tree = self.ensure_limit_ast(tree, limit=limit)
                
            return tree.sql(dialect="sqlite")
            
        except Exception:
            # Fallback to string manipulation if parse fails (for partial safety)
            # Just do basic cleanup
            s = re.sub(r"\s+", " ", s).strip()
            return s
