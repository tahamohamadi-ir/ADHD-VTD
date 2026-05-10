from __future__ import annotations

from _bootstrap_path import PROJECT_ROOT

from src.sql_validation.safety_validator import SQLSafetyValidator


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    print(f"PROJECT_ROOT={PROJECT_ROOT}")
    validator = SQLSafetyValidator()

    top_star = validator.validate("SELECT * FROM student_depression")
    print("top-level SELECT *:", top_star.ok, [i.message for i in top_star.issues])
    assert_true(not top_star.ok, "Top-level SELECT * must remain rejected.")

    cte_star = validator.validate(
        "WITH base AS (SELECT * FROM student_depression) "
        "SELECT COUNT(*) AS n, AVG(cgpa_10) AS avg_cgpa FROM base"
    )
    print("CTE-internal SELECT *:", cte_star.ok, [i.message for i in cte_star.issues])
    assert_true(cte_star.ok, "CTE-internal SELECT * should be allowed when final projection is explicit.")

    table_star = validator.validate("SELECT student_depression.* FROM student_depression")
    print("top-level table.*:", table_star.ok, [i.message for i in table_star.issues])
    assert_true(not table_star.ok, "Top-level table.* must be rejected.")

    count_star = validator.validate("SELECT COUNT(*) AS n FROM student_depression")
    print("COUNT(*):", count_star.ok, [i.message for i in count_star.issues])
    assert_true(count_star.ok, "COUNT(*) must remain allowed.")

    delete_sql = validator.validate("DELETE FROM student_depression")
    print("DELETE:", delete_sql.ok, [i.message for i in delete_sql.issues])
    assert_true(not delete_sql.ok, "DELETE must remain rejected.")

    print("Safety validator CTE hotfix checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
