from __future__ import annotations

SIMPLICITY_FIRST_RULES: str = (
    "Prefer the simplest SQL that answers the question. "
    "Do not add CASE WHEN, subqueries, CTEs, window functions, or computed percentages "
    "unless the question explicitly asks for them. "
    "For 'نسبت/درصد' questions prefer a direct ratio of two aggregates over nested CASE logic. "
    "Never invent extra grouping levels beyond the requested dimensions."
)

CORRECTION_EXAMPLES: tuple[tuple[str, str, str], ...] = (
    (
        "aggregate_in_where",
        "SELECT major FROM student_demographics WHERE COUNT(student_id) > 100",
        "Use GROUP BY with HAVING instead of an aggregate inside WHERE.",
        "SELECT major FROM student_demographics GROUP BY major HAVING COUNT(student_id) > 100",
    ),
    (
        "hallucinated_column",
        "SELECT AVG(salary) FROM student_depression",
        "The column does not exist; map to the closest real metric column in the schema.",
        "SELECT AVG(academic_pressure) FROM student_depression",
    ),
    (
        "missing_group_by",
        "SELECT gender, AVG(age) FROM student_depression",
        "Non-aggregated SELECT columns require GROUP BY.",
        "SELECT gender, AVG(age) FROM student_depression GROUP BY gender",
    ),
)


def render_simplicity_block(enabled: bool) -> list[str]:
    if not enabled:
        return []
    return [f"Simplicity rule: {SIMPLICITY_FIRST_RULES}"]


def render_correction_kb_block(enabled: bool) -> str:
    if not enabled:
        return ""
    lines = ["### Correction Examples (do not repeat these mistakes)"]
    for name, broken, logic, fixed in CORRECTION_EXAMPLES:
        lines.append(f"[{name}]")
        lines.append(f"Broken: {broken}")
        lines.append(f"Why: {logic}")
        lines.append(f"Fixed: {fixed}")
    return "\n".join(lines)
