"""
config.py
=========

Central configuration loader for the tools layer.
Loads environment variables with fallback defaults.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load .env if present
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


class Settings(BaseModel):
    # Application Environment
    APP_ENV: str = Field(default=os.getenv("APP_ENV", "development"))
    DATA_MODE: str = Field(default=os.getenv("DATA_MODE", "mock"))  # "mock" or "real"
    ML_SERVICE_URL: str = Field(
        default=os.getenv("ML_SERVICE_URL", "https://careguard-ml-latest.onrender.com")
    )

    # Groq LLM Configuration
    GROQ_API_KEY: Optional[str] = Field(default=os.getenv("GROQ_API_KEY"))
    GROQ_MODEL: str = Field(
        default=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    )
    GROQ_BASE_URL: str = Field(
        default=os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
    )

    # ChromaDB & Embeddings
    CHROMA_PERSIST_DIRECTORY: str = Field(
        default=os.getenv(
            "CHROMA_PERSIST_DIRECTORY",
            str(Path(__file__).resolve().parent.parent / "chroma_db"),
        )
    )
    EMBEDDING_MODEL: str = Field(
        default=os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    )

    # RAG Tuning Parameters
    RAG_TOP_K: int = Field(default=int(os.getenv("RAG_TOP_K", "10")))
    RAG_FINAL_K: int = Field(default=int(os.getenv("RAG_FINAL_K", "5")))
    RAG_EVIDENCE_THRESHOLD: float = Field(
        default=float(os.getenv("RAG_EVIDENCE_THRESHOLD", "0.70"))
    )

    # Database Configuration (for future real repository)
    DATABASE_URL: Optional[str] = Field(default=os.getenv("DATABASE_URL"))


settings = Settings()
