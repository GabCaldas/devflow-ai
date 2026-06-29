"""Agente Triador — atua como cerebro do Orquestrador.

Classifica o PR (risco/area) e decide QUAIS agentes devem rodar. Essa decisao
e o que torna o sistema agentico: o fluxo se adapta ao conteudo da mudanca.
"""
from app.llm.client import complete, parse_json
from app.schemas import TriageResponse

SYSTEM_PROMPT = """Voce e um tech lead que tria Pull Requests.
Analise o diff e classifique. Decida quais agentes especializados devem rodar:
- "reviewer": sempre que houver logica/codigo a revisar
- "testgen": quando ha codigo novo que merece testes
- "documenter": quando ha API/funcoes publicas que merecem documentacao

Responda SOMENTE com JSON valido:
{
  "risk_level": "low|medium|high",
  "affected_area": "area afetada",
  "summary": "resumo do que o PR faz",
  "recommended_agents": ["reviewer", "testgen", "documenter"]
}"""


async def triage_pr(diff: str, language: str | None = None) -> TriageResponse:
    user_prompt = f"Linguagem: {language or 'desconhecida'}\n\nDiff:\n{diff}"
    raw, provider = await complete(SYSTEM_PROMPT, user_prompt)
    data = parse_json(raw)
    return TriageResponse(
        risk_level=data.get("risk_level", "medium"),
        affected_area=data.get("affected_area", "desconhecida"),
        summary=data.get("summary", ""),
        recommended_agents=data.get("recommended_agents", ["reviewer"]),
        provider_used=provider,
    )
