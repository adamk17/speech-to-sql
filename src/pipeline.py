import psycopg2
import openai
from openai import OpenAI
import config
from database import Database
from agents.orchestrator import Orchestrator
from agents.query import QueryAgent, QueryResult
from agents.mutation import MutationAgent
from rag.retrieve import DocumentRetriever


class PipelineResult:
    def __init__(
        self,
        sql: str | None = None,
        columns: list | None = None,
        rows: list | None = None,
        message: str | None = None,
    ):
        self.sql = sql
        self.columns = columns or []
        self.rows = rows or []
        self.message = message


class Pipeline:
    def __init__(self, db: Database, client: OpenAI | None = None):
        self._db = db
        self._client = client or OpenAI(
            api_key=config.LLM_API_KEY,
            base_url=config.LLM_BASE_URL,
        )
        self._orchestrator = Orchestrator(client=self._client)
        self._retriever = DocumentRetriever()
        self._query_agent: QueryAgent | None = None
        self._mutation_agent: MutationAgent | None = None

    def _get_query_agent(self) -> QueryAgent:
        if self._query_agent is None:
            schema = self._db.get_schema()
            self._query_agent = QueryAgent(
                schema=schema,
                db=self._db,
                retriever=self._retriever,
                client=self._client,
            )
        return self._query_agent

    def _get_mutation_agent(self) -> MutationAgent:
        if self._mutation_agent is None:
            schema = self._db.get_schema()
            self._mutation_agent = MutationAgent(
                schema=schema,
                db=self._db,
                retriever=self._retriever,
                client=self._client,
            )
        return self._mutation_agent

    def _handle_empty_result(self, original_question: str) -> str | None:
        answer = input("No results found. Add sample data? [y/N]: ").strip().lower()
        if answer != "y":
            return None
        try:
            count = int(input("How many rows? ").strip())
        except ValueError:
            return "Invalid number."

        sql = self._get_mutation_agent().generate(
            f"Generate {count} rows for this query context: {original_question}"
        )
        if sql.startswith("ERROR:"):
            return f"Agent: {sql}"

        rows_affected = self._get_mutation_agent().execute(sql)
        return f"Inserted {rows_affected} rows."

    def _handle_mutation(self, question: str) -> PipelineResult:
        sql = self._get_mutation_agent().generate(question)
        if sql.startswith("ERROR:"):
            return PipelineResult(message=f"Agent: {sql}")

        answer = input("Execute? [y/N]: ").strip().lower()
        if answer != "y":
            return PipelineResult(message="Cancelled.")

        rows_affected = self._get_mutation_agent().execute(sql)
        return PipelineResult(message=f"Done. {rows_affected} rows affected.")

    def run(self, question: str) -> PipelineResult:
        try:
            print("Classifying intent...")
            intent = self._orchestrator.classify_intent(question)

            if intent == "mutation":
                print("Generating mutation query...")
                return self._handle_mutation(question)

            if intent == "query":
                print("Generating SQL query...")
                result: QueryResult = self._get_query_agent().run(question)

                if result.sql.startswith("ERROR:"):
                    return PipelineResult(message=f"Agent: {result.sql}")

                if result.is_empty:
                    message = self._handle_empty_result(question)
                    return PipelineResult(sql=result.sql, message=message)

                return PipelineResult(sql=result.sql, columns=result.columns, rows=result.rows)

            return PipelineResult(message="Could not determine intent. Please rephrase.")

        except psycopg2.OperationalError:
            return PipelineResult(message="Error: Cannot connect to database. Check your connection settings in .env.")
        except psycopg2.Error as e:
            return PipelineResult(message=f"Error: Database error: {e}")
        except openai.APITimeoutError:
            return PipelineResult(message="Error: LLM API request timed out. The model may be overloaded, try again.")
        except openai.APIConnectionError:
            return PipelineResult(message="Error: Cannot connect to LLM API. Check your internet connection.")
        except openai.AuthenticationError:
            return PipelineResult(message="Error: Invalid LLM API key. Check LLM_API_KEY in .env.")
        except openai.APIError as e:
            return PipelineResult(message=f"Error: LLM API error: {e}")
