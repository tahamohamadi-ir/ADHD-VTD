from __future__ import annotations

from src.utils.hashing import result_hash, sql_hash, text_hash
from src.utils.jsonl import append_jsonl, append_jsonl_batch, iter_jsonl, read_jsonl, write_jsonl


def test_jsonl_read_write_append_roundtrip(tmp_path):
    path = tmp_path / "records.jsonl"
    records = [{"id": 1, "text": "alpha"}, {"id": 2, "text": "بتا"}]

    assert write_jsonl(path, records) == 2
    append_jsonl(path, {"id": 3, "text": "gamma"})
    assert append_jsonl_batch(path, [{"id": 4}, {"id": 5}]) == 2

    loaded = read_jsonl(path)
    assert [row["id"] for row in loaded] == [1, 2, 3, 4, 5]
    assert list(iter_jsonl(path)) == loaded


def test_jsonl_missing_file_is_empty(tmp_path):
    missing = tmp_path / "missing.jsonl"

    assert read_jsonl(missing) == []
    assert list(iter_jsonl(missing)) == []


def test_sql_hash_normalizes_case_whitespace_and_semicolon():
    assert sql_hash(" SELECT  *  FROM student_depression; ") == sql_hash(
        "select * from STUDENT_DEPRESSION"
    )


def test_result_hash_is_stable_for_key_order_and_float_noise():
    left = [{"a": 1, "b": 1.123456789}]
    right = [{"b": 1.1234567891, "a": 1}]

    assert result_hash(left) == result_hash(right)


def test_text_hash_changes_with_content():
    assert text_hash("alpha") != text_hash("beta")
