from __future__ import annotations

from _bootstrap_path import PROJECT_ROOT
from src.sql_validation.safety_validator import SQLSafetyValidator
from src.sql_validation.syntax_validator import SQLSyntaxValidator
from src.sql_validation.schema_validator import SQLSchemaValidator


def show(sql: str) -> None:
    print("=" * 80)
    print(sql)
    for name, validator in [
        ("safety", SQLSafetyValidator()),
        ("syntax", SQLSyntaxValidator()),
        ("schema", SQLSchemaValidator()),
    ]:
        result = validator.validate(sql)
        print(name, result.ok, result.messages())


def main() -> int:
    show("SELECT COUNT(*) FROM student_depression")
    show("SELECT AVG(phq9_score) FROM clinical_assessments")
    show("DROP TABLE student_depression")
    show("SELECT * FROM student_depression")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
