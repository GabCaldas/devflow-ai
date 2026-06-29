from app.llm.client import complete, parse_json
from app.observability import observe
from app.schemas import ReviewResponse, ReviewIssue

SYSTEM_PROMPT = """You are a strict, objective senior code reviewer.
Analyze the diff and identify bugs, security flaws, performance issues and style
problems. Respond ONLY with valid JSON in this format:
{
  "summary": "short note on the overall quality",
  "issues": [
    {
      "severity": "low|medium|high",
      "category": "bug|security|style|performance",
      "message": "description of the problem",
      "suggestion": "how to fix it (optional)"
    }
  ]
}
If there are no problems, return an empty issues list."""


@observe(name="reviewer")
async def review_code(diff: str, language: str | None = None) -> ReviewResponse:
    user_prompt = f"Language: {language or 'unknown'}\n\nDiff:\n{diff}"
    raw, provider = await complete(SYSTEM_PROMPT, user_prompt)

    data = parse_json(raw)
    issues = [ReviewIssue(**issue) for issue in data.get("issues", [])]

    return ReviewResponse(
        summary=data.get("summary", ""),
        issues=issues,
        provider_used=provider,
    )
