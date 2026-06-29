"""Cliente LLM multi-provider.

Abstrai o provedor: tenta o principal (Groq) e, se falhar, cai pro fallback
(Gemini). Esse padrao de 'provider abstraction + fallback' e muito valorizado
em sistemas de producao porque evita ficar refem de um unico fornecedor e
aumenta a resiliencia.

Falamos com as APIs via HTTP direto (httpx), sem SDK, pra reduzir dependencias
e deixar claro o que esta acontecendo na rede.

Nota de design: NAO usamos o "modo JSON estrito" dos provedores. O validador
estrito do Groq chega a rejeitar a propria geracao quando o conteudo e grande
(ex: markdown com quebras de linha). Em vez disso pedimos JSON via prompt e
fazemos parsing tolerante (ver parse_json) — padrao mais robusto na pratica.
"""
import json
import re

import httpx

from app.config import settings


class LLMError(RuntimeError):
    """Erro quando nenhum provedor consegue responder."""


async def _call_groq(system: str, user: str) -> str:
    """Groq expoe uma API compativel com o formato OpenAI."""
    if not settings.groq_api_key:
        raise LLMError("GROQ_API_KEY ausente")

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {settings.groq_api_key}"}
    payload = {
        "model": settings.groq_model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.2,
    }
    async with httpx.AsyncClient(timeout=60) as http:
        resp = await http.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]


async def _call_gemini(system: str, user: str) -> str:
    """Gemini usa o endpoint generateContent."""
    if not settings.gemini_api_key:
        raise LLMError("GEMINI_API_KEY ausente")

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{settings.gemini_model}:generateContent?key={settings.gemini_api_key}"
    )
    payload = {
        "system_instruction": {"parts": [{"text": system}]},
        "contents": [{"parts": [{"text": user}]}],
        "generationConfig": {"temperature": 0.2},
    }
    async with httpx.AsyncClient(timeout=60) as http:
        resp = await http.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]


async def complete(system: str, user: str) -> tuple[str, str]:
    """Retorna (texto_resposta, provedor_usado).

    Ordem: provedor preferido -> o outro como fallback.
    """
    order = (
        ["groq", "gemini"]
        if settings.llm_provider == "groq"
        else ["gemini", "groq"]
    )
    callers = {"groq": _call_groq, "gemini": _call_gemini}

    errors: list[str] = []
    for provider in order:
        try:
            text = await callers[provider](system, user)
            return text, provider
        except httpx.HTTPStatusError as exc:  # erro HTTP da API: inclui corpo
            body = exc.response.text[:300]
            errors.append(f"{provider}: HTTP {exc.response.status_code} {body}")
        except Exception as exc:  # tenta o proximo provedor
            errors.append(f"{provider}: {type(exc).__name__}: {exc}")

    raise LLMError("Todos os provedores falharam | " + " | ".join(errors))


def parse_json(text: str) -> dict:
    """Parsing tolerante de JSON vindo do LLM.

    Lida com os casos comuns: cercas de codigo (```json ... ```) e texto extra
    antes/depois do objeto. Extrai do primeiro '{' ate o ultimo '}'.
    """
    cleaned = text.strip()
    # remove cercas de codigo, se houver
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.MULTILINE)
    # isola o objeto: do primeiro '{' ao ultimo '}'
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start != -1 and end > start:
        cleaned = cleaned[start : end + 1]

    # Tentativas progressivas de robustez (LLM embutindo codigo em JSON quebra
    # de varias formas: control chars e escapes invalidos como \d de regex):
    #  1) strict=False tolera quebras de linha/tabs literais dentro de strings
    #  2) escapa barras invertidas que nao formam um escape JSON valido
    try:
        return json.loads(cleaned, strict=False)
    except json.JSONDecodeError:
        fixed = re.sub(r'\\(?!["\\/bfnrtu])', r"\\\\", cleaned)
        return json.loads(fixed, strict=False)
