from openai import OpenAI
import config
from database import Database
from rag.retrieve import DocumentRetriever
from agents.base import BaseAgent


class MutationAgent(BaseAgent):
    SYSTEM_PROMPT = """You are an expert SQL assistant. Your job is to convert natural language requests (in Polish or English) into valid PostgreSQL mutation queries.

Rules:
- Return ONLY the SQL query, nothing else
- No explanations, no markdown, no code blocks
- Only INSERT, UPDATE, or DELETE statements
- Use only tables and columns that exist in the schema below
- Generate realistic, meaningful data that fits the context
- For foreign key columns: use NULL if the column is nullable and you don't know valid referenced values
- If the request is unclear or cannot be answered with the schema, return: ERROR: <reason>

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

    def _get_rag_context(self, request: str) -> str:
        docs = self._retriever.retrieve(request, n_results=3)
        return "\n\n---\n\n".join(docs)

    def generate(self, user_request: str) -> str:
        pg_docs = self._get_rag_context(user_request)
        system = self.SYSTEM_PROMPT.format(schema=self.schema, pg_docs=pg_docs)

        response = self._client.chat.completions.create(
            model=config.LLM_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_request},
            ],
            temperature=0,
            timeout=30,
        )

        return self._extract_sql(response.choices[0].message.content)

    def execute(self, sql: str) -> int:
        return self._db.execute_mutation(sql)