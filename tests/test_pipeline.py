import psycopg2
import openai
from unittest.mock import MagicMock, patch
from pipeline import Pipeline
from agents.query import QueryResult


class TestPipeline:
    def make_pipeline(self) -> Pipeline:
        mock_db = MagicMock()
        mock_client = MagicMock()
        pipeline = Pipeline(db=mock_db, client=mock_client)
        pipeline._orchestrator = MagicMock()
        pipeline._query_agent = MagicMock()
        pipeline._mutation_agent = MagicMock()
        return pipeline

    def make_query_result(self, rows=None, sql="SELECT 1") -> QueryResult:
        rows = rows or []
        columns = list(rows[0].keys()) if rows else []
        return QueryResult(columns=columns, rows=rows, sql=sql)

    def test_run_returns_query_result_on_query_intent(self):
        pipeline = self.make_pipeline()
        pipeline._orchestrator.classify_intent.return_value = "query"
        pipeline._query_agent.run.return_value = self.make_query_result(
            rows=[{"id": 1, "name": "Jan"}], sql="SELECT * FROM employees"
        )
        result = pipeline.run("show all employees")
        assert result.sql == "SELECT * FROM employees"
        assert result.rows == [{"id": 1, "name": "Jan"}]
        assert result.message is None

    def test_run_returns_error_message_when_agent_returns_error(self):
        pipeline = self.make_pipeline()
        pipeline._orchestrator.classify_intent.return_value = "query"
        pipeline._query_agent.run.return_value = self.make_query_result(sql="ERROR: unknown table")
        result = pipeline.run("show xyz")
        assert result.message is not None
        assert "ERROR:" in result.message

    def test_run_asks_user_on_empty_result_and_declines(self):
        pipeline = self.make_pipeline()
        pipeline._orchestrator.classify_intent.return_value = "query"
        pipeline._query_agent.run.return_value = self.make_query_result(rows=[], sql="SELECT * FROM employees")
        with patch("builtins.input", return_value="n"):
            result = pipeline.run("show employees without department")
        assert result.sql == "SELECT * FROM employees"
        assert result.message is None

    def test_run_inserts_data_on_empty_result_when_confirmed(self):
        pipeline = self.make_pipeline()
        pipeline._orchestrator.classify_intent.return_value = "query"
        pipeline._query_agent.run.return_value = self.make_query_result(rows=[], sql="SELECT * FROM employees")
        pipeline._mutation_agent.generate.return_value = "INSERT INTO employees VALUES (1, 'Jan')"
        pipeline._mutation_agent.execute.return_value = 3
        with patch("builtins.input", side_effect=["y", "3"]):
            result = pipeline.run("show employees without department")
        assert result.message == "Inserted 3 rows."

    def test_run_handles_mutation_intent_and_confirms(self):
        pipeline = self.make_pipeline()
        pipeline._orchestrator.classify_intent.return_value = "mutation"
        pipeline._mutation_agent.generate.return_value = "INSERT INTO employees VALUES (1, 'Jan')"
        pipeline._mutation_agent.execute.return_value = 1
        with patch("builtins.input", return_value="y"):
            result = pipeline.run("add employee Jan")
        assert result.message == "Done. 1 rows affected."

    def test_run_cancels_mutation_when_declined(self):
        pipeline = self.make_pipeline()
        pipeline._orchestrator.classify_intent.return_value = "mutation"
        pipeline._mutation_agent.generate.return_value = "INSERT INTO employees VALUES (1, 'Jan')"
        with patch("builtins.input", return_value="n"):
            result = pipeline.run("add employee Jan")
        assert result.message == "Cancelled."

    def test_run_returns_unknown_message_for_unknown_intent(self):
        pipeline = self.make_pipeline()
        pipeline._orchestrator.classify_intent.return_value = "unknown"
        result = pipeline.run("???")
        assert result.message is not None

    def test_run_handles_db_connection_error(self):
        pipeline = self.make_pipeline()
        pipeline._orchestrator.classify_intent.side_effect = psycopg2.OperationalError()
        result = pipeline.run("show employees")
        assert "Cannot connect to database" in result.message

    def test_run_handles_llm_api_connection_error(self):
        pipeline = self.make_pipeline()
        pipeline._orchestrator.classify_intent.side_effect = openai.APIConnectionError(request=MagicMock())
        result = pipeline.run("show employees")
        assert "Cannot connect to LLM API" in result.message

    def test_run_handles_llm_auth_error(self):
        pipeline = self.make_pipeline()
        pipeline._orchestrator.classify_intent.side_effect = openai.AuthenticationError(
            message="invalid key", response=MagicMock(), body={}
        )
        result = pipeline.run("show employees")
        assert "Invalid LLM API key" in result.message

    def test_run_handles_llm_timeout(self):
        pipeline = self.make_pipeline()
        pipeline._orchestrator.classify_intent.side_effect = openai.APITimeoutError(
            request=MagicMock()
        )
        result = pipeline.run("show employees")
        assert "timed out" in result.message