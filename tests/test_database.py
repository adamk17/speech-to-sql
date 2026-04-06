import pytest
from unittest.mock import patch, MagicMock
from database import Database


class TestDatabase:
    DB_PARAMS = dict(host="localhost", port="5432", dbname="test", user="u", password="p")

    MUTATION_QUERIES = [
        "INSERT INTO employees VALUES (1, 'Jan')",
        "UPDATE employees SET salary = 0",
        "DELETE FROM employees",
        "DROP TABLE employees",
        "ALTER TABLE employees ADD COLUMN x INT",
        "TRUNCATE employees",
    ]

    def make_db(self) -> Database:
        return Database(**self.DB_PARAMS)

    def make_mock_conn(self, rowcount=0):
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_cursor.fetchall.return_value = []
        mock_cursor.description = []
        mock_cursor.rowcount = rowcount

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        return mock_conn, mock_cursor

    def test_execute_select_blocks_mutation_statements(self):
        db = self.make_db()
        for sql in self.MUTATION_QUERIES:
            with pytest.raises(ValueError, match="Only SELECT"):
                db.execute_select(sql)

    def test_execute_select_allows_select(self):
        db = self.make_db()
        mock_conn, _ = self.make_mock_conn()
        with patch.object(db, "_get_connection", return_value=mock_conn):
            columns, rows = db.execute_select("SELECT 1")
        assert columns == []
        assert rows == []

    def test_execute_select_allows_cte(self):
        db = self.make_db()
        mock_conn, _ = self.make_mock_conn()
        with patch.object(db, "_get_connection", return_value=mock_conn):
            columns, rows = db.execute_select(
                "WITH cte AS (SELECT 1 AS n) SELECT * FROM cte"
            )
        assert columns == []
        assert rows == []

    def test_execute_select_allows_recursive_cte(self):
        db = self.make_db()
        mock_conn, _ = self.make_mock_conn()
        with patch.object(db, "_get_connection", return_value=mock_conn):
            columns, rows = db.execute_select(
                "WITH RECURSIVE t(n) AS (VALUES (1) UNION ALL SELECT n+1 FROM t WHERE n < 10) SELECT * FROM t"
            )
        assert columns == []
        assert rows == []

    def test_execute_mutation_blocks_select(self):
        db = self.make_db()
        with pytest.raises(ValueError, match="Only INSERT"):
            db.execute_mutation("SELECT * FROM employees")

    def test_execute_mutation_returns_rowcount(self):
        db = self.make_db()
        mock_conn, _ = self.make_mock_conn(rowcount=3)
        with patch.object(db, "_get_connection", return_value=mock_conn):
            affected = db.execute_mutation("INSERT INTO employees VALUES (1, 'Jan')")
        assert affected == 3
        mock_conn.commit.assert_called_once()

    def test_execute_mutation_update(self):
        db = self.make_db()
        mock_conn, _ = self.make_mock_conn(rowcount=5)
        with patch.object(db, "_get_connection", return_value=mock_conn):
            affected = db.execute_mutation("UPDATE employees SET salary = 0")
        assert affected == 5

    def test_execute_mutation_delete(self):
        db = self.make_db()
        mock_conn, _ = self.make_mock_conn(rowcount=2)
        with patch.object(db, "_get_connection", return_value=mock_conn):
            affected = db.execute_mutation("DELETE FROM employees WHERE id = 1")
        assert affected == 2

    def test_schema_fetched_once(self):
        db = self.make_db()
        mock_conn, _ = self.make_mock_conn()
        with patch.object(db, "_get_connection", return_value=mock_conn):
            db.get_schema()
            db.get_schema()
        assert mock_conn.cursor.call_count == 1