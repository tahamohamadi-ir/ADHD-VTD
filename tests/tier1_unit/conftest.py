"""Shared fixtures for tier1 unit tests."""
from __future__ import annotations

import pytest


@pytest.fixture
def sample_persian_questions() -> list[str]:
    """Common test questions in Persian."""
    return [
        "میانگین نمره افسردگی دانشجوهای زن چقدره?",
        "تعداد دانشجوهایی که ریسک بالا دارند",
        "چند درصد دانشجوها افسرده هستند?",
        "توزیع اضطراب بر اساس جنسیت",
        "بهترین معدل بین دانشجوها کیه?",
    ]


@pytest.fixture
def sample_safe_sqls() -> list[str]:
    """Known-safe SQL queries for validation tests."""
    return [
        "SELECT COUNT(*) FROM student_depression WHERE depression_flag = 1",
        "SELECT AVG(phq9_score) FROM student_depression",
        "SELECT gender, COUNT(*) FROM student_depression GROUP BY gender",
        "WITH dep AS (SELECT * FROM student_depression WHERE depression_flag = 1) SELECT COUNT(*) FROM dep",
    ]


@pytest.fixture
def sample_unsafe_sqls() -> list[str]:
    """Known-unsafe SQL queries for safety validation tests."""
    return [
        "DROP TABLE student_depression",
        "DELETE FROM student_depression WHERE id = 1",
        "INSERT INTO student_depression VALUES (1, 'test')",
        "UPDATE student_depression SET depression_flag = 0",
        "SELECT * FROM student_depression; DROP TABLE student_depression",
    ]
