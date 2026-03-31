import pytest
from unittest.mock import patch, MagicMock
import agent


def make_response(content: str):
    response = MagicMock()
    response.choices[0].message.content = content
    return response


class TestExtractSql:
    def test_plain_sql_unchanged(self):
        assert agent.extract_sql("SELECT * FROM employees") == "SELECT * FROM employees"

    def test_strips_markdown_sql_block(self):
        assert agent.extract_sql("```sql\nSELECT * FROM employees\n```") == "SELECT * FROM employees"

    def test_strips_markdown_generic_block(self):
        assert agent.extract_sql("```\nSELECT 1\n```") == "SELECT 1"

    def test_strips_whitespace(self):
        assert agent.extract_sql("  SELECT 1  ") == "SELECT 1"

    def test_error_prefix_preserved(self):
        assert agent.extract_sql("ERROR: table does not exist") == "ERROR: table does not exist"


class TestGetRagContext:
    def test_joins_chunks_with_separator(self):
        with patch("agent.retrieve", return_value=["chunk A", "chunk B", "chunk C"]):
            result = agent.get_rag_context("some query")
        assert "chunk A" in result
        assert "chunk B" in result
        assert "---" in result

    def test_empty_retrieve_returns_empty_string(self):
        with patch("agent.retrieve", return_value=[]):
            result = agent.get_rag_context("some query")
        assert result == ""


class TestAgentAsk:
    def test_returns_sql_from_model(self):
        with patch.object(agent.client.chat.completions, "create") as mock_create:
            mock_create.return_value = make_response("SELECT * FROM employees")
            with patch("database.get_schema", return_value="Table: employees\n  id (integer)"):
                with patch("agent.retrieve", return_value=["some pg docs"]):
                    result = agent.ask("show all employees")
        assert result == "SELECT * FROM employees"

    def test_strips_markdown_from_model_response(self):
        with patch.object(agent.client.chat.completions, "create") as mock_create:
            mock_create.return_value = make_response("```sql\nSELECT 1\n```")
            with patch("database.get_schema", return_value=""):
                with patch("agent.retrieve", return_value=[]):
                    result = agent.ask("test")
        assert result == "SELECT 1"

    def test_returns_error_prefix_unchanged(self):
        with patch.object(agent.client.chat.completions, "create") as mock_create:
            mock_create.return_value = make_response("ERROR: unknown table")
            with patch("database.get_schema", return_value=""):
                with patch("agent.retrieve", return_value=[]):
                    result = agent.ask("delete everything")
        assert result.startswith("ERROR:")

    def test_pg_docs_injected_into_prompt(self):
        with patch.object(agent.client.chat.completions, "create") as mock_create:
            mock_create.return_value = make_response("SELECT 1")
            with patch("database.get_schema", return_value=""):
                with patch("agent.retrieve", return_value=["RANK() example"]):
                    agent.ask("test")
        system_prompt = mock_create.call_args[1]["messages"][0]["content"]
        assert "RANK() example" in system_prompt
