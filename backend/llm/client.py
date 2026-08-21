"""
Backward-compatibility adapter for LLMClient.

Wraps the new abstract LLMProvider factory while preserving the API expected
by legacy orchestrator modules and ScriptedLLMClient test doubles.
"""
from __future__ import annotations

import logging
from typing import Any, Optional, Type, TypeVar

from pydantic import BaseModel

from llm.base import LLMExecutionTrace, LLMProvider
from llm.config import settings
from llm.errors import LLMProviderError, StructuredOutputError
from llm.factory import get_llm_provider

logger = logging.getLogger("agent.llm.client")

# Alias LLMError to LLMProviderError for backward-compatible try/except blocks
LLMError = LLMProviderError

T = TypeVar("T", bound=BaseModel)


class LLMClient(LLMProvider):
    """
    Backwards-compatible client wrapper around FallbackLLMProvider.
    Allows existing calls to complete_json and ScriptedLLMClient subclasses
    to operate seamlessly.
    """

    def __init__(self, model: Optional[str] = None, max_tokens: int = 2000):
        effective_model = model or settings.groq_model
        super().__init__(name="client_wrapper", model=effective_model)
        self.max_tokens = max_tokens
        self._provider: Optional[LLMProvider] = None

    def _get_provider(self) -> LLMProvider:
        if self._provider is None:
            self._provider = get_llm_provider()
        return self._provider

    def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: Optional[int] = None,
    ) -> dict[str, Any]:
        provider = self._get_provider()
        res = provider.complete_json(system_prompt, user_prompt, max_tokens=max_tokens or self.max_tokens)
        self.last_trace = provider.last_trace
        return res
