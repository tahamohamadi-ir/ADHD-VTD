from __future__ import annotations

from _bootstrap_path import PROJECT_ROOT

from src.nlu.persian_normalizer import PersianNormalizer
from src.nlu.safety_intent_detector import SafetyIntentDetector
from src.nlu.ambiguity_detector import AmbiguityDetector
from src.nlu.intent_classifier import IntentClassifier
from src.schema.value_linker import ValueLinker
from src.schema.schema_linker import SchemaLinker
from src.sql_validation.safety_validator import SQLSafetyValidator
from src.sql_validation.syntax_validator import SQLSyntaxValidator
from src.sql_validation.schema_validator import SQLSchemaValidator
from src.db.read_only_executor import ReadOnlyExecutor


def assert_true(value, message: str) -> None:
    if not value:
        raise AssertionError(message)


def main() -> int:
    print(f"PROJECT_ROOT={PROJECT_ROOT}")

    norm = PersianNormalizer().normalize_text("افسوردگی دانشجوها چند درصده؟")
    assert_true("افسردگی" in norm, "PersianNormalizer should fix افسوردگی -> افسردگی")

    safety = SafetyIntentDetector().detect("DROP TABLE student_depression")
    assert_true(not safety.is_safe, "Safety detector should reject DROP")

    amb = AmbiguityDetector().detect("یه آمار کلی بده")
    assert_true(amb.is_ambiguous, "Ambiguity detector should ask clarification for generic request")

    intent = IntentClassifier().classify("میانگین CGPA دانشجوهای افسرده چقدره؟")
    assert_true(intent.should_generate_sql, "Intent classifier should allow safe SQL-capable query")

    vl = ValueLinker().resolve_as_dicts("دانشجویان زن افسرده", ["student_depression.gender", "student_depression.depression_flag"])
    assert_true(any(x["resolved_value"] == "Female" for x in vl), "ValueLinker should map زن -> Female")
    assert_true(any(x["resolved_value"] == 1 for x in vl), "ValueLinker should map افسرده -> 1")

    linked = SchemaLinker().link("میانگین CGPA دانشجوهای افسرده چقدره؟")
    assert_true("student_depression" in linked.tables, "SchemaLinker should link student_depression")

    sql = "SELECT ROUND(AVG(cgpa_10), 2) FROM student_depression WHERE depression_flag = 1"
    assert_true(SQLSafetyValidator().validate(sql).ok, "SQLSafetyValidator should accept safe SELECT")
    assert_true(SQLSyntaxValidator().validate(sql).ok, "SQLSyntaxValidator should parse safe SELECT")
    assert_true(SQLSchemaValidator().validate(sql).ok, "SQLSchemaValidator should validate current table/columns")

    result = ReadOnlyExecutor().execute_readonly(sql)
    assert_true(result.ok, f"ReadOnlyExecutor should execute safe SQL. error={result.error}")

    print("Phase 1 foundation checks passed.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
