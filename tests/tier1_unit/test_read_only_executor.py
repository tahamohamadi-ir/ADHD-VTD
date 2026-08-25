"""Unit tests for ReadOnlyExecutor (mock DB)."""

from __future__ import annotations
import sqlite3
from unittest.mock import patch, MagicMock

import pytest

from src.db.read_only_executor import ReadOnlyExecutor
from src.db.sqlite_connection import get_readonly_connection


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


@pytest.fixture()
def stats_db_path(tmp_path):
    path = tmp_path / "stats.db"
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE t (x REAL)")
    conn.executemany("INSERT INTO t VALUES (?)", [(2,), (4,), (4,), (4,), (5,), (5,), (7,), (9,)])
    conn.commit()
    conn.close()
    return path


class TestStatsFunctions:
    def test_median_stddev_variance_through_executor(self, stats_db_path):
        executor = ReadOnlyExecutor(db_path=stats_db_path)
        result = executor.execute_readonly(
            "SELECT MEDIAN(x) AS median_x, STDDEV(x) AS stddev_x, "
            "VARIANCE(x) AS variance_x FROM t"
        )

        assert result.ok, result.error
        median_x, stddev_x, variance_x = list(result.rows[0].values())
        assert median_x == pytest.approx(4.5)
        assert stddev_x == pytest.approx(2.138089935299395)
        assert variance_x == pytest.approx(32 / 7)

    def test_stats_null_safe_on_empty_input(self, stats_db_path):
        executor = ReadOnlyExecutor(db_path=stats_db_path)
        result = executor.execute_readonly(
            "SELECT MEDIAN(x) AS median_x, STDDEV(x) AS stddev_x, "
            "VARIANCE(x) AS variance_x FROM t WHERE 0=1"
        )

        assert result.ok, result.error
        median_x, stddev_x, variance_x = list(result.rows[0].values())
        assert median_x is None
        assert stddev_x is None
        assert variance_x is None

    def test_query_only_still_enforced(self, stats_db_path):
        with get_readonly_connection(stats_db_path) as conn:
            assert conn.execute("PRAGMA query_only").fetchone()[0] == 1
            with pytest.raises(sqlite3.OperationalError):
                conn.execute("UPDATE t SET x = 0")
