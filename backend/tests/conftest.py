import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

import tools  # noqa: F401 populate registry
from llm.base import LLMExecutionTrace
from llm.client import LLMClient, LLMError


class ScriptedLLMClient(LLMClient):
    """
    Test double for LLMClient/LLMProvider. Returns a pre-scripted sequence of JSON
    responses instead of calling real LLM APIs, allowing offline deterministic testing.
    """

    def __init__(self, responses: list[dict] | None = None, raise_on_call: bool = False):
        super().__init__()
        self._responses = list(responses or [])
        self._raise_on_call = raise_on_call
        self.call_count = 0

    def complete_json(self, system_prompt: str, user_prompt: str, max_tokens=None) -> dict:
        self.call_count += 1
        if self._raise_on_call:
            self.last_trace = LLMExecutionTrace(
                provider="scripted_mock",
                model="mock_model",
                success=False,
                latency_ms=1.0,
                error_type="SimulatedLLMError",
            )
            raise LLMError("simulated LLM failure")
        if not self._responses:
            self.last_trace = LLMExecutionTrace(
                provider="scripted_mock",
                model="mock_model",
                success=False,
                latency_ms=1.0,
                error_type="ScriptExhausted",
            )
            raise LLMError("ScriptedLLMClient ran out of scripted responses")
        
        self.last_trace = LLMExecutionTrace(
            provider="scripted_mock",
            model="mock_model",
            success=True,
            latency_ms=1.0,
        )
        return self._responses.pop(0)


@pytest.fixture
def sample_claim():
    return {
        "provider_id": "ABC123",
        "procedure": "MRI",
        "diagnosis": "Lower back pain",
        "amount": 4800,
        "patient_id": "P001",
    }
