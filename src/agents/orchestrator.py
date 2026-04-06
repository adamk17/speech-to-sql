from openai import OpenAI
import config


class Orchestrator:
    INTENT_PROMPT = """Classify the user's intent as exactly one of: query, mutation, unknown.

- query: user wants to retrieve, list, show, find, or display data
- mutation: user wants to create, insert, add, update, modify, delete, or remove data
- unknown: cannot determine intent

Return only one word: query, mutation, or unknown."""

    def __init__(self, client: OpenAI | None = None):
        self._client = client or OpenAI(
            api_key=config.LLM_API_KEY,
            base_url=config.LLM_BASE_URL,
        )

    def classify_intent(self, user_question: str) -> str:
        response = self._client.chat.completions.create(
            model=config.LLM_MODEL,
            messages=[
                {"role": "system", "content": self.INTENT_PROMPT},
                {"role": "user", "content": user_question},
            ],
            temperature=0,
            timeout=30,
        )
        intent = response.choices[0].message.content.strip().lower()
        if intent not in ("query", "mutation"):
            return "unknown"
        return intent