from typing import Any, Dict, List, Optional
from src.reflexion.error_taxonomy import Taxon, classify_error

class SQLCritic:
    """Analyzes SQL failures and provides actionable feedback for repair."""

    def analyze(self, sql: str, error_msg: str, schema_context: Optional[str] = None) -> str:
        taxon = classify_error(error_msg)
        
        feedback = []
        feedback.append(f"The previous SQL query failed.")
        feedback.append(f"SQL Attempt: {sql}")
        feedback.append(f"Error Category: {taxon.category.value}")
        feedback.append(f"Error Detail: {error_msg}")
        
        if taxon.code == "no_such_table":
            feedback.append("Suggestion: Review the schema and ensure you are using the correct table names. Tables available in context should be used.")
        elif taxon.code == "no_such_column":
            feedback.append("Suggestion: The column you referenced does not exist in the specified table. Check the schema for correct column names.")
        elif taxon.category == "syntax_error":
            feedback.append("Suggestion: Check the SQL syntax, especially quotes, parentheses, and SQLite-specific keywords.")
            
        return "\n".join(feedback)

    def build_repair_prompt(self, feedback: str) -> str:
        return (
            "You are a SQL Repair Specialist. Based on the feedback below, "
            "please provide a corrected SQL query in JSON format: {\"sql\": \"...\"}\n\n"
            f"### Feedback:\n{feedback}\n\n"
            "Corrected SQL:"
        )
