"""Configuracao central: le variaveis de ambiente do arquivo .env.

Usar pydantic-settings deixa a config tipada e validada — boa pratica de
engenharia que aparece em projetos de producao.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Groq (provedor principal)
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"

    # Gemini (fallback)
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"

    # groq | gemini
    llm_provider: str = "groq"

    # GitHub: token pessoal (PAT) para ler PRs e postar comentarios
    github_token: str = ""
    # diffs muito grandes estouram o limite de tokens do free tier; truncamos
    max_diff_chars: int = 16000


settings = Settings()
