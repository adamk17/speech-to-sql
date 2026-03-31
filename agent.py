import re
from openai import OpenAI
import config
import database
from rag.retrieve import retrieve

client = OpenAI(
    api_key=config.LLM_API_KEY,
    base_url=config.LLM_BASE_URL,
)

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


def get_rag_context(question: str) -> str:
    docs = retrieve(question, n_results=3)
    return "\n\n---\n\n".join(docs)


def extract_sql(text: str) -> str:
    text = text.strip()
    # strip markdown code blocks if model returns them anyway
    match = re.search(r"```(?:sql)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return text


def ask(user_question: str) -> str:
    schema = database.get_schema()
    pg_docs = get_rag_context(user_question)
    system = SYSTEM_PROMPT.format(schema=schema, pg_docs=pg_docs)

    response = client.chat.completions.create(
        model=config.LLM_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_question},
        ],
        temperature=0,
    )

    raw = response.choices[0].message.content
    return extract_sql(raw)
