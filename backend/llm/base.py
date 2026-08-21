"""
Abstract Base LLM Provider Interface with Structured Generation and Execution Trace Support.
"""
from __future__ import annotations

import json
import logging
import re
import time
from abc import ABC, abstractmethod
from typing import Any, Optional, Type, TypeVar

from pydantic import BaseModel, Field, ValidationError

from llm.errors import StructuredOutputError

logger = logging.getLogger("agent.llm.base")

T = TypeVar("T", bound=BaseModel)


class LLMExecutionTrace(BaseModel):
    """Observability metadata recorded for every LLM call."""
    provider: str
    model: str
    success: bool
    latency_ms: float
    fallback_used: bool = False
    fallback_reason: Optional[str] = None
    retry_count: int = 0
    error_type: Optional[str] = None
    timestamp: float = Field(default_factory=time.time)


class LLMProvider(ABC):
    """Abstract interface that all LLM providers must implement."""

    def __init__(self, name: str, model: str):
        self.name = name
        self.model = model
        self.last_trace: Optional[LLMExecutionTrace] = None

    @abstractmethod
    def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: Optional[int] = None,
    ) -> dict[str, Any]:
        """Call the LLM and return raw parsed JSON dictionary."""
        pass

    def structured_generate(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: Type[T],
        max_tokens: Optional[int] = None,
    ) -> T:
        """
        Generates and validates output against a Pydantic model.
        Falls back to JSON completion and strict Pydantic parsing if native
        structured output is unavailable. Raises StructuredOutputError on failure.
        """
        json_dict = self.complete_json(system_prompt, user_prompt, max_tokens=max_tokens)
        return self._validate_model(json_dict, response_model)

    @staticmethod
    def _validate_model(data: dict[str, Any], response_model: Type[T]) -> T:
        try:
            return response_model.model_validate(data)
        except ValidationError as exc:
            logger.error("Structured output Pydantic validation failed: %s", exc)
            raise StructuredOutputError(
                f"Output failed schema validation for {response_model.__name__}: {exc}",
                provider="base",
            ) from exc

    @staticmethod
    def parse_raw_json(raw: str) -> dict[str, Any]:
        """Defensively extract and parse JSON block from LLM output."""
        cleaned = re.sub(r"^```(json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except json.JSONDecodeError:
                    pass
            logger.error("Could not parse LLM output as JSON: %s", raw[:500])
            raise StructuredOutputError(f"Unparseable JSON output: {raw[:200]}...", provider="base")
