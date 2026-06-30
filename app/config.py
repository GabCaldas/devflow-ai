from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"

    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"

    llm_provider: str = "groq"

    github_token: str = ""
    max_diff_chars: int = 16000

    rag_enabled: bool = True
    codebase_path: str = "."
    rag_top_k: int = 5
    rag_max_files: int = 1500
    rag_max_context_chars: int = 7000

    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "https://cloud.langfuse.com"


settings = Settings()
