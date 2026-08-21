"""
Retrying LLM Provider Wrapper and Factory.

Encapsulates the Groq provider.
Enforces strict error classification: retries up to max_retries for TransientLLMError.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from llm.base import LLMExecutionTrace, LLMProvider
from llm.config import settings
from llm.errors import TransientLLMError
from llm.groq_provider import GroqLLMProvider

logger = logging.getLogger("agent.llm.factory")


class RetryingGroqProvider(LLMProvider):
    def __init__(
        self,
        max_retries: Optional[int] = None,
    ):
        self.primary = GroqLLMProvider()
        self.max_retries = max_retries if max_retries is not None else settings.max_retries
        super().__init__(name="groq_wrapper", model=self.primary.model)
        self.last_trace: Optional[LLMExecutionTrace] = None
        self.trace_history: list[LLMExecutionTrace] = []

    def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: Optional[int] = None,
    ) -> dict[str, Any]:
        last_exception: Optional[TransientLLMError] = None
        retries = 0

        # Attempt primary provider with bounded retries for transient errors
        for attempt in range(self.max_retries + 1):
            try:
                res = self.primary.complete_json(system_prompt, user_prompt, max_tokens=max_tokens)
                if self.primary.last_trace:
                    self.primary.last_trace.retry_count = retries
                    self.last_trace = self.primary.last_trace
                    self.trace_history.append(self.last_trace)
                return res

            except TransientLLMError as exc:
                last_exception = exc
                retries = attempt + 1
                if attempt < self.max_retries:
                    logger.warning(
                        "[LLM] Groq request failed attempt %d/%d (%s). Retrying...",
                        attempt + 1,
                        self.max_retries + 1,
                        exc,
                    )
                else:
                    logger.warning(
                        "[LLM] Final failure: Groq exhausted %d retries (%s).",
                        self.max_retries,
                        exc,
                    )

        # If we exhausted all retries, raise the last exception
        raise last_exception or TransientLLMError("Groq failed after retries")


def get_llm_provider() -> LLMProvider:
    """Factory function returning the configured primary provider instance."""
    return RetryingGroqProvider()
