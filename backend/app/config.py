from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    # Database
    database_url: str

    # JWT
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7

    # App
    app_name: str = "ClaimGuard AI"
    app_version: str = "1.0.0"
    debug: bool = True
    ml_service_url: Optional[str] = None
    
    # Agent/LLM Configuration (optional, for agentic features)
    app_env: str = "production"
    data_mode: str = "real"
    llm_primary_provider: str = "groq"
    groq_api_key: Optional[str] = None
    groq_api_key_copilot: Optional[str] = None
    groq_model: str = "openai/gpt-oss-120b"
    groq_base_url: str = "https://api.groq.com/openai/v1"
    llm_fallback_provider: str = "gemini"
    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-3-flash-preview"
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    llm_fast_model: str = "llama-3.1-8b-instant"
    llm_reasoning_model: str = "openai/gpt-oss-120b"
    llm_critic_model: str = "openai/gpt-oss-20b"
    llm_timeout_seconds: float = 60.0
    max_llm_retries: int = 2
    max_investigation_iterations: int = 5
    max_critic_revisions: int = 2

    class Config:
        env_file = ".env"
        extra = "allow"  # Allow extra fields from .env


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
