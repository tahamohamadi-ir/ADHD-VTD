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
    TABLE_SCOPED_COLUMN_FIXES: dict[tuple[str, str], str] = {
        ("student_depression", "family_history"): "family_history_mental_illness",
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
        tables: dict[str, str] = {}
        for table in tree.find_all(exp.Table):
            table_name = table.name
            tables[table.alias_or_name] = table_name
            tables[table_name] = table_name
        used_tables = set(tables.values())

        for col in tree.find_all(exp.Column):
            col_name = col.name.lower()
            table_ref = col.table
            real_table = tables.get(table_ref, table_ref) if table_ref else None
            if real_table and (real_table, col_name) in self.TABLE_SCOPED_COLUMN_FIXES:
                replacement = self.TABLE_SCOPED_COLUMN_FIXES[(real_table, col_name)]
                col.set("this", exp.Identifier(this=replacement, quoted=col.this.args.get("quoted")))
                continue
            if (
                not table_ref
                and len(used_tables) == 1
                and ("student_depression", col_name) in self.TABLE_SCOPED_COLUMN_FIXES
                and "student_depression" in used_tables
            ):
                replacement = self.TABLE_SCOPED_COLUMN_FIXES[("student_depression", col_name)]
                col.set("this", exp.Identifier(this=replacement, quoted=col.this.args.get("quoted")))
                continue
            if col_name in self.COLUMN_FIXES:
                # Replace with correct name
                col.set("this", exp.Identifier(this=self.COLUMN_FIXES[col_name], quoted=col.this.args.get("quoted")))
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

    def normalize_decimal_aggregates_ast(self, tree: exp.Expression) -> exp.Expression:
        """Round decimal aggregate projections to the project-standard 2 decimals."""
        if not isinstance(tree, exp.Select):
            return tree

        rewritten_expressions: list[exp.Expression] = []
        changed = False
        for projection in tree.expressions:
            alias_name = projection.alias if isinstance(projection, exp.Alias) else None
            expression = projection.this if isinstance(projection, exp.Alias) else projection
            if self._should_round_projection(expression):
                rounded = exp.Round(
                    this=expression.copy(),
                    decimals=exp.Literal.number(2),
                )
                if alias_name:
                    rewritten_expressions.append(exp.alias_(rounded, alias_name, quoted=False))
                else:
                    rewritten_expressions.append(rounded)
                changed = True
            else:
                rewritten_expressions.append(projection)

        if changed:
            tree.set("expressions", rewritten_expressions)
        return tree

    def _should_round_projection(self, expression: exp.Expression) -> bool:
        if isinstance(expression, exp.Round) or any(isinstance(node, exp.Round) for node in expression.walk()):
            return False
        if any(isinstance(node, exp.Window) for node in expression.walk()):
            return False
        if isinstance(expression, exp.Avg):
            return True
        has_ratio = any(isinstance(node, exp.Div) for node in expression.walk())
        has_sum = any(isinstance(node, exp.Sum) for node in expression.walk())
        has_count = any(isinstance(node, exp.Count) for node in expression.walk())
        has_avg = any(isinstance(node, exp.Avg) for node in expression.walk())
        return (has_ratio and (has_sum or has_count)) or (
            isinstance(expression, exp.Mul) and has_avg
        )

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
            tree = self.normalize_decimal_aggregates_ast(tree)
            
            if add_limit:
                tree = self.ensure_limit_ast(tree, limit=limit)
                
            return tree.sql(dialect="sqlite")
            
        except Exception:
            # Fallback to string manipulation if parse fails (for partial safety)
            # Just do basic cleanup
            s = re.sub(r"\s+", " ", s).strip()
            return s

    def rewrite_for_question(
        self,
        sql: str,
        *,
        question: str,
        add_limit: bool = True,
        limit: int = 100,
    ) -> str:
        rewritten = self.rewrite(sql, add_limit=add_limit, limit=limit)
        if self._is_dataset_only_depression_question(question):
            rewritten = self._remove_simple_depression_flag_filter(rewritten)
        if self._is_global_total_mental_health_count_question(question):
            rewritten = self._remove_where_and_limit_from_global_count(rewritten)
        return rewritten

    def _is_dataset_only_depression_question(self, question: str) -> bool:
        q = (question or "").lower()
        dataset_terms = (
            "\u062f\u06cc\u062a\u0627\u0633\u062a",
            "\u062f\u0627\u062f\u0647",
            "\u062c\u062f\u0648\u0644",
            "dataset",
            "student_depression",
        )
        depression_terms = ("\u0627\u0641\u0633\u0631\u062f\u06af\u06cc", "depression")
        explicit_positive_terms = (
            "\u0627\u0641\u0633\u0631\u062f\u06af\u06cc \u062f\u0627\u0631\u062f",
            "\u0627\u0641\u0633\u0631\u062f\u06af\u06cc \u062f\u0627\u0631\u0646\u062f",
            "\u062f\u0627\u0631\u0627\u06cc \u0627\u0641\u0633\u0631\u062f\u06af\u06cc",
            "\u0627\u0641\u0633\u0631\u062f\u0647 \u0648 \u063a\u06cc\u0631\u0627\u0641\u0633\u0631\u062f\u0647",
            "\u0627\u0641\u0633\u0631\u062f\u0647 \u0648 \u063a\u06cc\u0631 \u0627\u0641\u0633\u0631\u062f\u0647",
            "who are depressed",
            "with depression",
        )
        return (
            any(term in q for term in dataset_terms)
            and any(term in q for term in depression_terms)
            and not any(term in q for term in explicit_positive_terms)
        )

    def _remove_simple_depression_flag_filter(self, sql: str) -> str:
        s = sql
        s = re.sub(
            r"\bWHERE\s+depression_flag\s*=\s*1\s+AND\s+",
            "WHERE ",
            s,
            flags=re.IGNORECASE,
        )
        s = re.sub(
            r"\s+AND\s+depression_flag\s*=\s*1(?=\s+(GROUP\s+BY|ORDER\s+BY|HAVING|LIMIT)\b|$)",
            "",
            s,
            flags=re.IGNORECASE,
        )
        s = re.sub(
            r"\bWHERE\s+depression_flag\s*=\s*1(?=\s+(GROUP\s+BY|ORDER\s+BY|HAVING|LIMIT)\b|$)",
            "",
            s,
            flags=re.IGNORECASE,
        )
        return re.sub(r"\s+", " ", s).strip()

    def _is_global_total_mental_health_count_question(self, question: str) -> bool:
        q = (question or "").lower()
        count_terms = ("count", "\u062a\u0639\u062f\u0627\u062f")
        total_terms = ("total", "all", "\u06a9\u0644")
        record_terms = ("record", "\u0631\u06a9\u0648\u0631\u062f")
        global_prevalence_terms = (
            "global prevalence",
            "\u0634\u06cc\u0648\u0639 \u062c\u0647\u0627\u0646\u06cc",
        )
        mental_health_terms = (
            "mental health",
            "\u0633\u0644\u0627\u0645\u062a \u0631\u0648\u0627\u0646",
        )
        specific_disorder_terms = (
            "depression",
            "anxiety",
            "bipolar",
            "schizophrenia",
            "eating disorder",
            "\u0627\u0641\u0633\u0631\u062f\u06af\u06cc",
            "\u0627\u0636\u0637\u0631\u0627\u0628",
            "\u062f\u0648\u0642\u0637\u0628\u06cc",
            "\u0627\u0633\u06a9\u06cc\u0632\u0648\u0641\u0631\u0646\u06cc",
            "\u0627\u062e\u062a\u0644\u0627\u0644 \u062e\u0648\u0631\u062f\u0646",
        )
        return (
            any(term in q for term in count_terms)
            and any(term in q for term in total_terms)
            and any(term in q for term in record_terms)
            and any(term in q for term in global_prevalence_terms)
            and any(term in q for term in mental_health_terms)
            and not any(term in q for term in specific_disorder_terms)
        )

    def _remove_where_and_limit_from_global_count(self, sql: str) -> str:
        if not re.search(r"\bFROM\s+country_prevalence_long\b", sql, flags=re.IGNORECASE):
            return sql
        if not re.search(r"\bCOUNT\s*\(", sql, flags=re.IGNORECASE):
            return sql
        s = re.sub(
            r"\s+WHERE\s+.+?(?=\s+(GROUP\s+BY|ORDER\s+BY|HAVING|LIMIT)\b|$)",
            "",
            sql,
            count=1,
            flags=re.IGNORECASE,
        )
        s = re.sub(r"\s+LIMIT\s+\d+\b", "", s, flags=re.IGNORECASE)
        return re.sub(r"\s+", " ", s).strip()
