"""Agente Gerador de Testes — escreve testes automatizados para o codigo novo.

Como o Documentador, este agente retorna TEXTO PURO (o codigo dos testes), nao
JSON. Embutir codigo dentro de uma string JSON e fragil: o LLM quase sempre
quebra o JSON com aspas/barras/escapes invalidos. JSON fica reservado para os
agentes com saida curta e estruturada (Revisor, Triador).
"""
import re

from app.llm.client import complete
from app.schemas import TestGenResponse

# framework idiomatico por linguagem (heuristica simples)
FRAMEWORK_BY_LANG = {
    "python": "pytest",
    "javascript": "jest",
    "typescript": "jest",
    "java": "junit",
}

SYSTEM_PROMPT = """Voce e um engenheiro especialista em testes automatizados.
A partir do diff, gere testes que cubram os principais caminhos e casos de borda,
usando o framework idiomatico da linguagem (pytest para Python, jest para JS).
Responda APENAS com o codigo dos testes, sem explicacoes fora do codigo."""


def _strip_code_fence(text: str) -> str:
    """Remove cercas de markdown (```python ... ```) se o modelo as incluir."""
    text = text.strip()
    text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


async def generate_tests(diff: str, language: str | None = None) -> TestGenResponse:
    user_prompt = f"Linguagem: {language or 'desconhecida'}\n\nDiff:\n{diff}"
    raw, provider = await complete(SYSTEM_PROMPT, user_prompt)
    framework = FRAMEWORK_BY_LANG.get((language or "").lower(), "auto")
    return TestGenResponse(
        framework=framework,
        tests_code=_strip_code_fence(raw),
        provider_used=provider,
    )
