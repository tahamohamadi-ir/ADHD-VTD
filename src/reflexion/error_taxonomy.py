from enum import Enum
from pydantic import BaseModel


class ErrorCategory(str, Enum):
    SYNTAX = "syntax_error"
    SCHEMA = "schema_mismatch"
    SAFETY = "safety_violation"
    EXECUTION = "execution_failure"
    EMPTY_RESULT = "empty_result"  # Sometimes considered an error if gold exists
    LOGIC = "logic_error"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


class Taxon(BaseModel):
    category: ErrorCategory
    code: str
    description_fa: str
    description_en: str
    is_retryable: bool


ERROR_TAXONOMY = {
    "no_such_table": Taxon(
        category=ErrorCategory.SCHEMA,
        code="no_such_table",
        description_fa="نام جدول در پایگاه داده یافت نشد.",
        description_en="Table name not found in database.",
        is_retryable=True,
    ),
    "no_such_column": Taxon(
        category=ErrorCategory.SCHEMA,
        code="no_such_column",
        description_fa="نام ستون در جدول مورد نظر یافت نشد.",
        description_en="Column name not found in table.",
        is_retryable=True,
    ),
    "syntax_error": Taxon(
        category=ErrorCategory.SYNTAX,
        code="syntax_error",
        description_fa="خطای نوشتاری در کوئری SQL.",
        description_en="SQL syntax error.",
        is_retryable=True,
    ),
    "safety_violation": Taxon(
        category=ErrorCategory.SAFETY,
        code="safety_violation",
        description_fa="تلاش برای دسترسی غیرمجاز یا مخرب.",
        description_en="Unauthorized or destructive query attempt.",
        is_retryable=False,
    ),
}


def classify_error(error_msg: str) -> Taxon:
    msg_lower = error_msg.lower()
    if "no such table" in msg_lower:
        return ERROR_TAXONOMY["no_such_table"]
    if "no such column" in msg_lower:
        return ERROR_TAXONOMY["no_such_column"]
    if "syntax error" in msg_lower:
        return ERROR_TAXONOMY["syntax_error"]
    if "not allowed" in msg_lower or "safety" in msg_lower:
        return ERROR_TAXONOMY["safety_violation"]

    return Taxon(
        category=ErrorCategory.UNKNOWN,
        code="generic_error",
        description_fa="خطای نامشخص در هنگام پردازش.",
        description_en="Unknown error during processing.",
        is_retryable=True,
    )
