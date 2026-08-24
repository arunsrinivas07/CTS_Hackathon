"""
Centralized Configuration for LLM Providers and Agent Execution.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

# Load .env file if present
_env_path = Path(__file__).resolve().parents[2] / ".env"  # Go up 2 levels from config.py to backend/
if _env_path.is_file():
    try:
        from dotenv import load_dotenv
        load_dotenv(_env_path)
    except ImportError:
        # Fallback simple parser if python-dotenv is not installed
        with open(_env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ[k.strip()] = v.strip()


@dataclass
class LLMSettings:
    # Application Environment
    app_env: str = os.environ.get("APP_ENV", "development")
    data_mode: str = os.environ.get("DATA_MODE", "mock")
    ml_service_url: str = os.environ.get("ML_SERVICE_URL", "http://localhost:8000")

    # Use consistent naming with backend config
    llm_primary_provider: str = os.environ.get("LLM_PRIMARY_PROVIDER", "groq")
    primary_provider: str = os.environ.get("LLM_PRIMARY_PROVIDER", "groq")  # Alias for compatibility
    llm_fallback_provider: str = os.environ.get("LLM_FALLBACK_PROVIDER", "gemini")
    fallback_provider: str = os.environ.get("LLM_FALLBACK_PROVIDER", "gemini")  # Alias for compatibility

    # Groq Settings (Verified working model: openai/gpt-oss-120b)
    groq_api_key: str = (os.environ.get("GROQ_API_KEY") or os.environ.get("GROQ_API_KEY_COPILOT") or "").strip()
    groq_model: str = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
    # Role-specific Groq models
    fast_model: str = os.environ.get(
        "LLM_FAST_MODEL",
        "llama-3.1-8b-instant"
    )

    reasoning_model: str = os.environ.get(
        "LLM_REASONING_MODEL",
        "openai/gpt-oss-120b"
    )

    critic_model: str = os.environ.get(
        "LLM_CRITIC_MODEL",
        "llama-3.3-70b-versatile"
)
    groq_base_url: str = os.environ.get("GROQ_BASE_URL", "https://api.groq.com/openai/v1")

    # Gemini Settings (Fallback)
    gemini_api_key: str = (os.environ.get("GEMINI_API_KEY") or "").strip()
    gemini_model: str = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash")
    gemini_base_url: str = os.environ.get("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/")

    # ChromaDB & Embeddings
    chroma_persist_directory: str = os.environ.get(
        "CHROMA_PERSIST_DIRECTORY",
        str(Path(__file__).resolve().parent.parent.parent / "chroma_db"),
    )
    embedding_model: str = os.environ.get("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

    # RAG Tuning Parameters
    rag_top_k: int = int(os.environ.get("RAG_TOP_K", "10"))
    rag_final_k: int = int(os.environ.get("RAG_FINAL_K", "5"))
    rag_evidence_threshold: float = float(os.environ.get("RAG_EVIDENCE_THRESHOLD", "0.70"))

    # Database Configuration (for future real repository)
    database_url: str = os.environ.get("DATABASE_URL", "")

    # Execution Caps & Timeouts
    timeout_seconds: float = float(os.environ.get("LLM_TIMEOUT_SECONDS", "60.0"))
    max_retries: int = int(os.environ.get("MAX_LLM_RETRIES", "2"))
    max_investigation_iterations: int = int(os.environ.get("MAX_INVESTIGATION_ITERATIONS", "5"))
    max_critic_revisions: int = int(os.environ.get("MAX_CRITIC_REVISIONS", "2"))


settings = LLMSettings()
