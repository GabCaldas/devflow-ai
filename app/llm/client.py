import json
import re

import httpx

from app.config import settings
from app.observability import observe, record_generation


class LLMError(RuntimeError):
    pass


@observe(as_type="generation", name="groq")
async def _call_groq(system: str, user: str) -> str:
    if not settings.groq_api_key:
        raise LLMError("GROQ_API_KEY is missing")

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

    usage = data.get("usage", {})
    record_generation(
        model=settings.groq_model,
        usage_details={
            "input": usage.get("prompt_tokens", 0),
            "output": usage.get("completion_tokens", 0),
            "total": usage.get("total_tokens", 0),
        },
    )
    return data["choices"][0]["message"]["content"]


@observe(as_type="generation", name="gemini")
async def _call_gemini(system: str, user: str) -> str:
    if not settings.gemini_api_key:
        raise LLMError("GEMINI_API_KEY is missing")

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

    usage = data.get("usageMetadata", {})
    record_generation(
        model=settings.gemini_model,
        usage_details={
            "input": usage.get("promptTokenCount", 0),
            "output": usage.get("candidatesTokenCount", 0),
            "total": usage.get("totalTokenCount", 0),
        },
    )
    return data["candidates"][0]["content"]["parts"][0]["text"]


async def complete(system: str, user: str) -> tuple[str, str]:
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
        except httpx.HTTPStatusError as exc:
            body = exc.response.text[:300]
            errors.append(f"{provider}: HTTP {exc.response.status_code} {body}")
        except Exception as exc:
            errors.append(f"{provider}: {type(exc).__name__}: {exc}")

    raise LLMError("All providers failed | " + " | ".join(errors))


def parse_json(text: str) -> dict:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.MULTILINE)
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start != -1 and end > start:
        cleaned = cleaned[start : end + 1]
    try:
        return json.loads(cleaned, strict=False)
    except json.JSONDecodeError:
        fixed = re.sub(r'\\(?!["\\/bfnrtu])', r"\\\\", cleaned)
        return json.loads(fixed, strict=False)
