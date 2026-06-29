"""Agente Revisor — o primeiro agente do sistema.

Responsabilidade unica: receber um diff de codigo e devolver uma revisao
estruturada (resumo + lista de problemas). Na Fase 2 ele vira um no dentro
do grafo LangGraph, ao lado dos agentes de Teste, Documentacao e Triagem.
"""
from app.llm.client import complete, parse_json
from app.schemas import ReviewResponse, ReviewIssue

SYSTEM_PROMPT = """Voce e um revisor de codigo senior, rigoroso e objetivo.
Analise o diff fornecido e identifique bugs, falhas de seguranca, problemas de
performance e de estilo. Responda SOMENTE com um JSON valido no formato:
{
  "summary": "resumo curto da qualidade geral",
  "issues": [
    {
      "severity": "low|medium|high",
      "category": "bug|security|style|performance",
      "message": "descricao do problema",
      "suggestion": "como corrigir (opcional)"
    }
  ]
}
Se nao houver problemas, retorne uma lista issues vazia."""


async def review_code(diff: str, language: str | None = None) -> ReviewResponse:
    """Roda o agente revisor sobre um diff."""
    user_prompt = f"Linguagem: {language or 'desconhecida'}\n\nDiff:\n{diff}"
    raw, provider = await complete(SYSTEM_PROMPT, user_prompt)

    data = parse_json(raw)  # provedores foram instruidos a devolver JSON
    issues = [ReviewIssue(**issue) for issue in data.get("issues", [])]

    return ReviewResponse(
        summary=data.get("summary", ""),
        issues=issues,
        provider_used=provider,
    )
