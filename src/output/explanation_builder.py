from typing import Any, Dict


def build_explanation(state: Dict[str, Any]) -> str | None:
    """Build a simple Persian explanation of the SQL execution."""
    action = state.get("actual_action", "generate_sql")
    if action != "generate_sql":
        return None

    sql = state.get("generated_sql")
    if not sql:
        return None

    explanation = f"کوئری اجرا شده:\n```sql\n{sql}\n```\n"

    # Try to extract assumptions if available from parsed payload
    parsed_payload = state.get("parsed_payload")
    if parsed_payload and isinstance(parsed_payload, dict):
        assumptions = parsed_payload.get("assumptions")
        if assumptions:
            explanation += "\n**فرضیات در نظر گرفته شده:**\n"
            if isinstance(assumptions, list):
                for assumption in assumptions:
                    explanation += f"- {assumption}\n"
            else:
                explanation += f"- {assumptions}\n"

    return explanation
