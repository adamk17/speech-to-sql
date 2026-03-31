import pytest
from unittest.mock import patch, MagicMock
import database


MUTATION_QUERIES = [
    "INSERT INTO employees VALUES (1, 'Jan')",
    "UPDATE employees SET salary = 0",
    "DELETE FROM employees",
    "DROP TABLE employees",
    "ALTER TABLE employees ADD COLUMN x INT",
    "TRUNCATE employees",
]


class TestExecuteSelect:
    def test_blocks_mutation_statements(self):
        for sql in MUTATION_QUERIES:
            with pytest.raises(ValueError, match="Only SELECT"):
                database.execute_select(sql)

    def test_allows_select(self):
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_cursor.fetchall.return_value = []
        mock_cursor.description = []

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with patch("database.get_connection", return_value=mock_conn):
            columns, rows = database.execute_select("SELECT 1")

        assert columns == []
        assert rows == []

    def test_allows_cte(self):
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_cursor.fetchall.return_value = []
        mock_cursor.description = []

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with patch("database.get_connection", return_value=mock_conn):
            columns, rows = database.execute_select(
                "WITH cte AS (SELECT 1 AS n) SELECT * FROM cte"
            )

        assert columns == []
        assert rows == []

    def test_allows_recursive_cte(self):
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_cursor.fetchall.return_value = []
        mock_cursor.description = []

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with patch("database.get_connection", return_value=mock_conn):
            columns, rows = database.execute_select(
                "WITH RECURSIVE t(n) AS (VALUES (1) UNION ALL SELECT n+1 FROM t WHERE n < 10) SELECT * FROM t"
            )

        assert columns == []
        assert rows == []
