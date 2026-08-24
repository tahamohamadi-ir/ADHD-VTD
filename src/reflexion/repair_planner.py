from src.reflexion.error_taxonomy import ErrorCategory, classify_error


class RepairPlanner:
    """Decides the strategy for repairing a failed SQL query."""

    def plan(self, sql: str, error_msg: str) -> str:
        taxon = classify_error(error_msg)

        if taxon.category == ErrorCategory.SCHEMA:
            return "Re-examine schema linking and schema metadata for correct identifiers."
        if taxon.category == ErrorCategory.SYNTAX:
            return "Perform strict syntax check and rewrite using standard SQLite dialact."
        if taxon.category == ErrorCategory.LOGIC:
            return "Review the question intent and mapping to SQL logic (joins, filters)."

        return "General repair: check for typical LLM SQL hallucinations."
