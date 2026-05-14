"""Unit tests for ReadOnlyExecutor (mock DB)."""
from __future__ import annotations
import pytest
from unittest.mock import patch, MagicMock
from src.db.read_only_executor import ReadOnlyExecutor

class TestSafetyGate:
    def test_rejects_unsafe_sql(self):
        executor = ReadOnlyExecutor(db_path="dummy.db")
        result = executor.execute_readonly("DROP TABLE student_depression")
        assert not result.ok
        assert result.error is not None

    def test_rejects_delete(self):
        executor = ReadOnlyExecutor(db_path="dummy.db")
        result = executor.execute_readonly("DELETE FROM t")
        assert not result.ok

class TestValidExecution:
    def test_valid_sql_with_mock_db(self):
        """Test execution with a mocked database connection."""
        mock_row = {"count": 42}
        mock_cursor = MagicMock()
        mock_cursor.fetchmany.return_value = [mock_row]
        mock_conn = MagicMock()
        mock_conn.execute.return_value = mock_cursor
        mock_conn.__enter__ = lambda s: s
        mock_conn.__exit__ = MagicMock(return_value=False)

        with patch("src.db.read_only_executor.get_readonly_connection", return_value=mock_conn):
            executor = ReadOnlyExecutor(db_path="test.db")
            result = executor.execute_readonly("SELECT COUNT(*) as count FROM student_depression")
            assert result.ok

class TestGoldSQL:
    def test_missing_gold_sql(self):
        executor = ReadOnlyExecutor(db_path="dummy.db")
        result = executor.execute_gold_sql({})
        assert not result.ok
        assert "gold_sql" in (result.error or "").lower()
