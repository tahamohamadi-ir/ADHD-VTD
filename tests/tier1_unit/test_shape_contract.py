from __future__ import annotations

from src.core.query_shape import QueryShapeContract
from src.sql_validation.shape_contract import SQLShapeContractValidator


def _validate(sql: str, contract: QueryShapeContract):
    return SQLShapeContractValidator().validate(sql, contract)


def test_scalar_count_star_is_accepted():
    result = _validate(
        "SELECT COUNT(*) AS total_records FROM student_depression",
        QueryShapeContract.scalar(),
    )

    assert result.ok


def test_scalar_avg_is_accepted():
    result = _validate(
        "SELECT ROUND(AVG(age), 2) AS avg_age FROM student_depression",
        QueryShapeContract.scalar(),
    )

    assert result.ok


def test_scalar_group_by_is_rejected():
    result = _validate(
        "SELECT depression_flag, COUNT(*) AS n FROM student_depression GROUP BY depression_flag",
        QueryShapeContract.scalar(),
    )

    assert not result.ok
    assert any(issue.code == "SHAPE_CONTRACT_FORBIDS_GROUP_BY" for issue in result.issues)


def test_scalar_hidden_where_is_rejected_when_filters_forbidden():
    result = _validate(
        "SELECT COUNT(*) AS total_records FROM student_depression WHERE depression_flag = 1",
        QueryShapeContract.scalar(allow_filters=False),
    )

    assert not result.ok
    assert any(issue.code == "SHAPE_CONTRACT_FORBIDS_WHERE" for issue in result.issues)


def test_grouped_query_is_accepted_when_group_by_required():
    result = _validate(
        "SELECT gender, COUNT(*) AS n FROM student_depression GROUP BY gender",
        QueryShapeContract.grouped(dimensions=["gender"]),
    )

    assert result.ok


def test_ranking_query_requires_order_by():
    result = _validate(
        "SELECT country_name, AVG(prevalence_pct) AS avg_prevalence FROM country_prevalence_long GROUP BY country_name LIMIT 10",
        QueryShapeContract.ranking(require_limit=True),
    )

    assert not result.ok
    assert any(issue.code == "SHAPE_CONTRACT_REQUIRES_ORDER_BY" for issue in result.issues)


def test_raw_rows_requires_limit():
    result = _validate(
        "SELECT age, gender FROM student_depression",
        QueryShapeContract.raw_rows(),
    )

    assert not result.ok
    assert any(issue.code == "SHAPE_CONTRACT_REQUIRES_LIMIT" for issue in result.issues)
