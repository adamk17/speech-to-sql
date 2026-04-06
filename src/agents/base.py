import re


class BaseAgent:
    def _extract_sql(self, text: str) -> str:
        text = text.strip()
        match = re.search(r"```(?:sql)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return text