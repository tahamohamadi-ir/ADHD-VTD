from __future__ import annotations

from _bootstrap_path import PROJECT_ROOT
from src.schema.schema_linker import SchemaLinker


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    print(f"PROJECT_ROOT={PROJECT_ROOT}")

    linker = SchemaLinker()

    result = linker.link("میانگین CGPA دانشجوهای افسرده چقدره؟")
    print(result.model_dump())
    assert_true("student_depression.cgpa_10" in result.columns, "SchemaLinker should link CGPA to student_depression.cgpa_10")
    assert_true("student_depression.depression_flag" in result.columns, "SchemaLinker should link افسرده to student_depression.depression_flag")
    assert_true("student_depression" in result.tables, "SchemaLinker should include student_depression table")

    result = linker.link("شیوع اضطراب در کشورها")
    print(result.model_dump())
    assert_true(
        "country_prevalence_long.disorder" in result.columns
        or "country_prevalence_wide.anxiety_pct" in result.columns,
        "SchemaLinker should link anxiety prevalence to country prevalence schema",
    )

    result = linker.link("نمره امتحان دانشجوها بر اساس ساعت خواب")
    print(result.model_dump())
    assert_true("student_habits_performance.exam_score" in result.columns, "SchemaLinker should link exam score")
    assert_true(
        any(c.endswith(".sleep_hours") or c.endswith(".sleep_mid_hours") or c.endswith(".sleep_duration_category") for c in result.columns),
        "SchemaLinker should link sleep columns",
    )

    print("Phase 1 schema linker hotfix checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
