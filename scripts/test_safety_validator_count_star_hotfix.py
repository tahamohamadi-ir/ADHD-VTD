from __future__ import annotations

from _bootstrap_path import PROJECT_ROOT

from src.sql_validation.safety_validator import SQLSafetyValidator


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def show(label: str, result) -> None:
    print(label + ":", result.ok, [i.message for i in result.issues])


def main() -> int:
    print(f"PROJECT_ROOT={PROJECT_ROOT}")
    validator = SQLSafetyValidator()

    count_star = validator.validate("SELECT COUNT(*) AS n FROM student_depression")
    show("COUNT(*)", count_star)
    assert_true(count_star.ok, "COUNT(*) must be allowed; it is not raw SELECT *.")

    count_with_filter = validator.validate(
        "SELECT gender, COUNT(*) AS n FROM student_depression GROUP BY gender ORDER BY n DESC"
    )
    show("GROUP BY COUNT(*)", count_with_filter)
    assert_true(count_with_filter.ok, "Grouped COUNT(*) must be allowed.")

    top_star = validator.validate("SELECT * FROM student_depression")
    show("Top-level SELECT *", top_star)
    assert_true(not top_star.ok, "Top-level SELECT * must remain rejected.")

    table_star = validator.validate("SELECT student_depression.* FROM student_depression")
    show("Top-level table.*", table_star)
    assert_true(not table_star.ok, "Top-level table.* must remain rejected.")

    cte_star = validator.validate(
        "WITH base AS (SELECT * FROM student_depression) "
        "SELECT COUNT(*) AS n, AVG(cgpa_10) AS avg_cgpa FROM base"
    )
    show("CTE-internal SELECT *", cte_star)
    assert_true(cte_star.ok, "CTE-internal SELECT * should be allowed when final projection is explicit.")

    delete_sql = validator.validate("DELETE FROM student_depression")
    show("DELETE", delete_sql)
    assert_true(not delete_sql.ok, "DELETE must remain rejected.")

    print("Safety validator COUNT(*) hotfix checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
