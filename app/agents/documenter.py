from app.llm.client import complete
from app.schemas import DocResponse

SYSTEM_PROMPT = """You are a technical writer. From the diff, generate clear
documentation in MARKDOWN: docstrings for functions/classes and a short usage note.
Respond ONLY with the documentation markdown, with no extra comments."""


async def generate_docs(diff: str, language: str | None = None) -> DocResponse:
    user_prompt = f"Language: {language or 'unknown'}\n\nDiff:\n{diff}"
    raw, provider = await complete(SYSTEM_PROMPT, user_prompt)
    return DocResponse(documentation=raw.strip(), provider_used=provider)
