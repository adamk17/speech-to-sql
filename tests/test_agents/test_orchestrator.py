from unittest.mock import MagicMock
from agents.orchestrator import Orchestrator


class TestOrchestrator:
    def make_client(self, response_text: str) -> MagicMock:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value.choices[0].message.content = response_text
        return mock_client

    def test_classifies_query_intent(self):
        orchestrator = Orchestrator(client=self.make_client("query"))
        assert orchestrator.classify_intent("show all employees") == "query"

    def test_classifies_mutation_intent(self):
        orchestrator = Orchestrator(client=self.make_client("mutation"))
        assert orchestrator.classify_intent("add 5 employees") == "mutation"

    def test_returns_unknown_for_unexpected_response(self):
        orchestrator = Orchestrator(client=self.make_client("something else"))
        assert orchestrator.classify_intent("???") == "unknown"

    def test_normalizes_response_to_lowercase(self):
        orchestrator = Orchestrator(client=self.make_client("  QUERY  "))
        assert orchestrator.classify_intent("list users") == "query"