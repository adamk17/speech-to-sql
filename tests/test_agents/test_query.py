from unittest.mock import MagicMock
from agents.query import QueryAgent, QueryResult
from database import Database
from rag.retrieve import DocumentRetriever


class TestQueryAgent:
    DB_PARAMS = dict(host="localhost", port="5432", dbname="test", user="u", password="p")

    def make_agent(self, llm_response: str, retriever_docs: list | None = None) -> QueryAgent:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value.choices[0].message.content = llm_response

        mock_retriever = MagicMock(spec=DocumentRetriever)
        mock_retriever.retrieve.return_value = retriever_docs or []

        mock_db = MagicMock(spec=Database)
        mock_db.execute_select.return_value = ([], [])

        return QueryAgent(
            schema="Table: employees\n  id (integer)",
            db=mock_db,
            retriever=mock_retriever,
            client=mock_client,
        )

    def test_extract_sql_plain(self):
        agent = self.make_agent("SELECT 1")
        assert agent._extract_sql("SELECT * FROM employees") == "SELECT * FROM employees"

    def test_extract_sql_strips_markdown(self):
        agent = self.make_agent("SELECT 1")
        assert agent._extract_sql("```sql\nSELECT 1\n```") == "SELECT 1"

    def test_extract_sql_strips_generic_block(self):
        agent = self.make_agent("SELECT 1")
        assert agent._extract_sql("```\nSELECT 1\n```") == "SELECT 1"

    def test_get_rag_context_joins_with_separator(self):
        agent = self.make_agent("SELECT 1", retriever_docs=["chunk A", "chunk B"])
        result = agent._get_rag_context("some question")
        assert "chunk A" in result
        assert "chunk B" in result
        assert "---" in result

    def test_get_rag_context_empty_returns_empty_string(self):
        agent = self.make_agent("SELECT 1", retriever_docs=[])
        assert agent._get_rag_context("some question") == ""

    def test_run_returns_query_result(self):
        agent = self.make_agent("SELECT * FROM employees")
        agent._db.execute_select.return_value = (["id", "name"], [{"id": 1, "name": "Jan"}])
        result = agent.run("show all employees")
        assert isinstance(result, QueryResult)
        assert result.sql == "SELECT * FROM employees"
        assert result.rows == [{"id": 1, "name": "Jan"}]
        assert result.is_empty is False

    def test_run_detects_empty_result(self):
        agent = self.make_agent("SELECT * FROM employees")
        result = agent.run("show all employees")
        assert result.is_empty is True

    def test_run_injects_pg_docs_into_prompt(self):
        agent = self.make_agent("SELECT 1", retriever_docs=["RANK() example"])
        agent.run("show employees")
        call_args = agent._client.chat.completions.create.call_args[1]
        system_prompt = call_args["messages"][0]["content"]
        assert "RANK() example" in system_prompt