"""
Gemini LLM Provider (FALLBACK).

Connects to Gemini API using an OpenAI-compatible interface.
Serves as the fallback provider when Groq rate limits or fails.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Optional

import httpx

from app.llm.base import LLMExecutionTrace, LLMProvider
from app.llm.config import settings
from app.llm.errors import (
    AuthenticationError,
    InvalidRequestError,
    LLMProviderError,
    NetworkError,
    RateLimitError,
    ServiceUnavailableError,
    StructuredOutputError,
    TimeoutError,
)

logger = logging.getLogger("agent.llm.gemini")


class GeminiLLMProvider(LLMProvider):
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        role: str = "generic",
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        model_name = model or settings.gemini_model
        super().__init__(name="gemini", model=model_name, role=role)
        self.api_key = (api_key or settings.gemini_api_key or "").strip()
        
        # Validate API key
        if not self.api_key:
            raise AuthenticationError(
                "Gemini API key is not configured. Please set GEMINI_API_KEY in your .env file.",
                provider=self.name,
                status_code=401
            )
        
        self.base_url = (base_url or settings.gemini_base_url).rstrip("/")
        self.timeout = timeout or settings.timeout_seconds

    def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: Optional[int] = None,
    ) -> dict[str, Any]:
        start_time = time.time()
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": max_tokens or 2000,
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(url, headers=headers, json=payload)

            latency_ms = (time.time() - start_time) * 1000.0

            if response.status_code == 401 or response.status_code == 403:
                err = AuthenticationError("Gemini API authentication failed", provider=self.name, status_code=response.status_code)
                self.last_trace = LLMExecutionTrace(provider=self.name, model=self.model, success=False, latency_ms=latency_ms, error_type="AuthenticationError")
                raise err
            elif response.status_code == 429:
                err = RateLimitError("Gemini rate limit exceeded", provider=self.name, status_code=response.status_code)
                self.last_trace = LLMExecutionTrace(provider=self.name, model=self.model, success=False, latency_ms=latency_ms, error_type="RateLimitError")
                raise err
            elif response.status_code >= 500:
                err = ServiceUnavailableError(f"Gemini service error {response.status_code}", provider=self.name, status_code=response.status_code)
                self.last_trace = LLMExecutionTrace(provider=self.name, model=self.model, success=False, latency_ms=latency_ms, error_type="ServiceUnavailableError")
                raise err
            elif response.status_code >= 400:
                err = InvalidRequestError(f"Gemini request error {response.status_code}: {response.text}", provider=self.name, status_code=response.status_code)
                self.last_trace = LLMExecutionTrace(provider=self.name, model=self.model, success=False, latency_ms=latency_ms, error_type="InvalidRequestError")
                raise err

            data = response.json()
            content = data["choices"][0]["message"]["content"]
            parsed = self.parse_raw_json(content)

            self.last_trace = LLMExecutionTrace(
                provider=self.name,
                model=self.model,
                success=True,
                latency_ms=latency_ms,
            )
            return parsed

        except (httpx.TimeoutException, TimeoutError) as exc:
            latency_ms = (time.time() - start_time) * 1000.0
            self.last_trace = LLMExecutionTrace(provider=self.name, model=self.model, success=False, latency_ms=latency_ms, error_type="TimeoutError")
            raise TimeoutError(f"Gemini call timed out: {exc}", provider=self.name) from exc
        except (httpx.NetworkError, httpx.RequestError) as exc:
            latency_ms = (time.time() - start_time) * 1000.0
            self.last_trace = LLMExecutionTrace(provider=self.name, model=self.model, success=False, latency_ms=latency_ms, error_type="NetworkError")
            raise NetworkError(f"Gemini network error: {exc}", provider=self.name) from exc
        except LLMProviderError:
            raise
        except Exception as exc:
            latency_ms = (time.time() - start_time) * 1000.0
            self.last_trace = LLMExecutionTrace(provider=self.name, model=self.model, success=False, latency_ms=latency_ms, error_type=type(exc).__name__)
            raise StructuredOutputError(f"Gemini output parsing failed: {exc}", provider=self.name) from exc
