"""
llm_provider.py
===============

LLM Provider Abstraction.
Primary: Groq API
Graceful Fallback: Deterministic / Rule-based execution when no LLM API is available.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import httpx

from app.llm.config import settings
from app.utils.tool_helpers import logger


class BaseLLMProvider(ABC):
    """Abstract interface for LLM completion providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier."""
        pass

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 1024,
    ) -> Optional[str]:
        """Generate a text completion."""
        pass


class GroqProvider(BaseLLMProvider):
    """Groq API LLM Provider."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> None:
        self.api_key = api_key or settings.groq_api_key
        self.model = model or settings.groq_model
        self.base_url = (base_url or settings.groq_base_url).rstrip("/")

    @property
    def name(self) -> str:
        return f"Groq ({self.model})"

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 1024,
    ) -> Optional[str]:
        if not self.api_key:
            raise ValueError("GROQ_API_KEY is not configured.")

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        with httpx.Client(timeout=15.0) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]


class FallbackLLMProvider(BaseLLMProvider):
    """
    Manages primary (Groq) LLM.
    If it fails or is unconfigured, safely returns None to trigger deterministic logic.
    """

    def __init__(
        self,
        primary: Optional[BaseLLMProvider] = None,
        fallback: Optional[BaseLLMProvider] = None,
    ) -> None:
        self.primary = primary or GroqProvider()
        self._last_used_provider: Optional[str] = None

    @property
    def name(self) -> str:
        return self._last_used_provider or "FallbackLLMProvider(Groq)"

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 1024,
    ) -> Optional[str]:
        try:
            result = self.primary.generate(
                prompt, system_prompt, temperature, max_tokens
            )
            self._last_used_provider = self.primary.name
            return result
        except Exception as groq_err:
            logger.warning(
                "Groq LLM provider failed or unavailable (%s). Operating in deterministic fallback mode.",
                groq_err,
            )

        self._last_used_provider = "deterministic_fallback"
        return None
