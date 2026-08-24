from __future__ import annotations

from src.core.query_shape import QueryShape, QueryShapeContract


def test_scalar_contract_forbids_hidden_shape_changes_by_default():
    contract = QueryShapeContract.scalar()

    assert contract.shape == QueryShape.SCALAR
    assert contract.max_rows == 1
    assert contract.forbid_group_by
    assert contract.forbid_limit
    assert contract.forbid_where


def test_grouped_contract_requires_requested_dimensions():
    contract = QueryShapeContract.grouped(dimensions=["gender"])

    assert contract.shape == QueryShape.GROUPED
    assert contract.require_group_by
    assert contract.min_group_by_dimensions == 1
    assert contract.required_dimensions == ["gender"]


def test_matrix_contract_requires_at_least_two_dimensions():
    contract = QueryShapeContract.matrix(dimensions=["gender"])

    assert contract.shape == QueryShape.MATRIX
    assert contract.require_group_by
    assert contract.min_group_by_dimensions == 2


def test_raw_rows_contract_requires_limit():
    contract = QueryShapeContract.raw_rows()

    assert contract.shape == QueryShape.RAW_ROWS
    assert contract.require_limit
    assert contract.forbid_group_by
