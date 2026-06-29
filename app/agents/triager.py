from app.llm.client import complete, parse_json
from app.schemas import TriageResponse

SYSTEM_PROMPT = """You are a tech lead triaging Pull Requests.
Analyze the diff and classify it. Decide which specialized agents should run:
- "reviewer": whenever there is logic/code to review
- "testgen": when there is new code that deserves tests
- "documenter": when there are public APIs/functions that deserve documentation

Respond ONLY with valid JSON:
{
  "risk_level": "low|medium|high",
  "affected_area": "affected area",
  "summary": "summary of what the PR does",
  "recommended_agents": ["reviewer", "testgen", "documenter"]
}"""


async def triage_pr(diff: str, language: str | None = None) -> TriageResponse:
    user_prompt = f"Language: {language or 'unknown'}\n\nDiff:\n{diff}"
    raw, provider = await complete(SYSTEM_PROMPT, user_prompt)
    data = parse_json(raw)
    return TriageResponse(
        risk_level=data.get("risk_level", "medium"),
        affected_area=data.get("affected_area", "unknown"),
        summary=data.get("summary", ""),
        recommended_agents=data.get("recommended_agents", ["reviewer"]),
        provider_used=provider,
    )
