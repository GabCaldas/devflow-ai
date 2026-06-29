"""Agente Documentador — gera documentacao/docstrings para o codigo novo.

Diferente dos outros agentes, este retorna MARKDOWN PURO (nao JSON). A saida e
um campo unico e longo; pedir JSON aqui so adiciona fragilidade (escapar quebras
de linha, aspas, etc.). Texto direto e mais robusto.
"""
from app.llm.client import complete
from app.schemas import DocResponse

SYSTEM_PROMPT = """Voce e um redator tecnico. A partir do diff, gere documentacao
clara em MARKDOWN: docstrings para funcoes/classes e uma breve explicacao de uso.
Responda APENAS com o markdown da documentacao, sem comentarios extras."""


async def generate_docs(diff: str, language: str | None = None) -> DocResponse:
    user_prompt = f"Linguagem: {language or 'desconhecida'}\n\nDiff:\n{diff}"
    raw, provider = await complete(SYSTEM_PROMPT, user_prompt)
    return DocResponse(documentation=raw.strip(), provider_used=provider)
