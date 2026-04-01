from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ── Application ───────────────────────────────────────────
    app_name: str = "LangChain DeepAgent"
    app_version: str = "1.0.0"
    debug: bool = False
    log_level: str = "INFO"

    # ── Ollama ────────────────────────────────────────────────
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:3b"
    ollama_temperature: float = 0.0

    # ── Agent ─────────────────────────────────────────────────
    agent_recursion_limit: int = 25
    skills_dir: str = ".deepagents/skills"

    # ── Redis ─────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # ── Rate Limiting ─────────────────────────────────────────
    rate_limit_requests: int = 10   # max requests per window
    rate_limit_seconds: int = 60    # window size in seconds

    # ── CORS ──────────────────────────────────────────────────
    cors_origins: list[str] = ["*"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
