from unittest.mock import MagicMock
from agents.mutation import MutationAgent
from database import Database
from rag.retrieve import DocumentRetriever


class TestMutationAgent:
    DB_PARAMS = dict(host="localhost", port="5432", dbname="test", user="u", password="p")

    def make_agent(self, llm_response: str, retriever_docs: list | None = None) -> MutationAgent:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value.choices[0].message.content = llm_response

        mock_retriever = MagicMock(spec=DocumentRetriever)
        mock_retriever.retrieve.return_value = retriever_docs or []

        mock_db = MagicMock(spec=Database)
        mock_db.execute_mutation.return_value = 0

        return MutationAgent(
            schema="Table: employees\n  id (integer)",
            db=mock_db,
            retriever=mock_retriever,
            client=mock_client,
        )

    def test_extract_sql_plain(self):
        agent = self.make_agent("INSERT INTO employees VALUES (1)")
        assert agent._extract_sql("INSERT INTO employees VALUES (1)") == "INSERT INTO employees VALUES (1)"

    def test_extract_sql_strips_markdown(self):
        agent = self.make_agent("INSERT INTO employees VALUES (1)")
        assert agent._extract_sql("```sql\nINSERT INTO employees VALUES (1)\n```") == "INSERT INTO employees VALUES (1)"

    def test_generate_returns_sql(self):
        agent = self.make_agent("INSERT INTO employees VALUES (1, 'Jan')")
        result = agent.generate("add employee Jan")
        assert result == "INSERT INTO employees VALUES (1, 'Jan')"

    def test_generate_strips_markdown(self):
        agent = self.make_agent("```sql\nINSERT INTO employees VALUES (1)\n```")
        result = agent.generate("add employee")
        assert result == "INSERT INTO employees VALUES (1)"

    def test_generate_injects_pg_docs_into_prompt(self):
        agent = self.make_agent("INSERT INTO employees VALUES (1)", retriever_docs=["INSERT syntax"])
        agent.generate("add employee")
        call_args = agent._client.chat.completions.create.call_args[1]
        system_prompt = call_args["messages"][0]["content"]
        assert "INSERT syntax" in system_prompt

    def test_execute_calls_db_and_returns_rowcount(self):
        agent = self.make_agent("INSERT INTO employees VALUES (1)")
        agent._db.execute_mutation.return_value = 5
        affected = agent.execute("INSERT INTO employees VALUES (1)")
        assert affected == 5
        agent._db.execute_mutation.assert_called_once_with("INSERT INTO employees VALUES (1)")