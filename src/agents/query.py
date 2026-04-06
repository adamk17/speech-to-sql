from openai import OpenAI
import config
from database import Database
from rag.retrieve import DocumentRetriever
from agents.base import BaseAgent


class QueryResult:
    def __init__(self, columns: list, rows: list, sql: str):
        self.columns = columns
        self.rows = rows
        self.sql = sql
        self.is_empty = len(rows) == 0


class QueryAgent(BaseAgent):
    SYSTEM_PROMPT = """You are an expert SQL assistant. Your job is to convert natural language questions (in Polish or English) into valid PostgreSQL SELECT queries.

Rules:
- Return ONLY the SQL query, nothing else
- No explanations, no markdown, no code blocks
- Only SELECT statements - never INSERT, UPDATE, DELETE, DROP, etc.
- Use only tables and columns that exist in the schema below
- If the question is unclear or cannot be answered with the schema, return: ERROR: <reason>

Database schema:
{schema}

Relevant PostgreSQL documentation:
{pg_docs}
"""

    def __init__(
        self,
        schema: str,
        db: Database,
        retriever: DocumentRetriever,
        client: OpenAI | None = None,
    ):
        self.schema = schema
        self._db = db
        self._retriever = retriever
        self._client = client or OpenAI(
            api_key=config.LLM_API_KEY,
            base_url=config.LLM_BASE_URL,
        )

    def _get_rag_context(self, question: str) -> str:
        docs = self._retriever.retrieve(question, n_results=3)
        return "\n\n---\n\n".join(docs)

    def run(self, user_question: str) -> QueryResult:
        pg_docs = self._get_rag_context(user_question)
        system = self.SYSTEM_PROMPT.format(schema=self.schema, pg_docs=pg_docs)

        response = self._client.chat.completions.create(
            model=config.LLM_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_question},
            ],
            temperature=0,
            timeout=30,
        )

        sql = self._extract_sql(response.choices[0].message.content)
        columns, rows = self._db.execute_select(sql)
        return QueryResult(columns=columns, rows=rows, sql=sql)
