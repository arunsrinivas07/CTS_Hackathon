"""
Structured Exception Hierarchy for LLM Providers.

Strictly separates transient/recoverable errors (which trigger fallback to Groq)
from non-transient errors (which halt execution and do NOT trigger fallback).
"""
from __future__ import annotations

from typing import Optional


class LLMProviderError(Exception):
    """Base exception for all LLM provider errors."""

    def __init__(self, message: str, provider: Optional[str] = None, status_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.provider = provider
        self.status_code = status_code


class TransientLLMError(LLMProviderError):
    """Base for recoverable/transient errors that should trigger fallback."""
    pass


class RateLimitError(TransientLLMError):
    """Provider rate limit or quota exceeded (e.g. HTTP 429)."""
    pass


class TimeoutError(TransientLLMError):
    """LLM API call timed out."""
    pass


class ServiceUnavailableError(TransientLLMError):
    """Provider service temporarily unavailable or internal server error (e.g. HTTP 500, 502, 503, 504)."""
    pass


class NetworkError(TransientLLMError):
    """Connection error or low-level network failure."""
    pass


class NonTransientLLMError(LLMProviderError):
    """Base for non-recoverable errors that should NOT trigger fallback."""
    pass


class AuthenticationError(NonTransientLLMError):
    """Invalid API key or unauthorized access (e.g. HTTP 401, 403)."""
    pass


class InvalidRequestError(NonTransientLLMError):
    """Malformed request payload or unsupported parameters (e.g. HTTP 400)."""
    pass


class StructuredOutputError(NonTransientLLMError):
    """LLM output failed Pydantic schema validation or JSON parsing."""
    pass
