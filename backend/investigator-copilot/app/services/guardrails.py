"""
Guardrails applied before and after processing a Copilot question.

Scope for this MVP:
- Basic prompt-injection pattern detection on the incoming question.
- Enforcing that only the authorized investigation_id is accessed.
- Preventing the Copilot from asserting fraud/final decisions in outgoing text
  (belt-and-suspenders on top of prompt-level instructions in copilot_service).

This is intentionally simple/rule-based for a two-day MVP. It is NOT a
replacement for a production-grade safety layer.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


class GuardrailViolation(Exception):
    """Raised when a request fails a guardrail check and must be blocked."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


_INJECTION_PATTERNS = [
    r"ignore (all|any|previous) instructions",
    r"you are now",
    r"disregard (the )?(system|previous) prompt",
    r"reveal (your|the) (system prompt|instructions)",
    r"act as (an? )?(unrestricted|unfiltered)",
]

_UNSUPPORTED_CONCLUSION_PHRASES = [
    "this is fraud",
    "this is fraudulent",
    "reject this claim",
    "deny this claim",
    "approve this claim",
]


@dataclass
class GuardrailCheckResult:
    ok: bool
    reason: Optional[str] = None


def check_question_for_injection(question: str) -> GuardrailCheckResult:
    lowered = question.lower()
    for pattern in _INJECTION_PATTERNS:
        if re.search(pattern, lowered):
            return GuardrailCheckResult(
                ok=False,
                reason="The question appears to contain an instruction-override attempt and was blocked.",
            )
    return GuardrailCheckResult(ok=True)


def check_investigation_access(requested_id: str, resolved_id: Optional[str]) -> GuardrailCheckResult:
    """Confirms the Copilot is only touching the single, authorized
    investigation named in the request — never a different one."""
    if resolved_id is None:
        return GuardrailCheckResult(ok=False, reason=f"Investigation '{requested_id}' was not found or is not accessible.")
    if resolved_id != requested_id:
        return GuardrailCheckResult(ok=False, reason="Resolved investigation does not match the requested investigation_id.")
    return GuardrailCheckResult(ok=True)


def sanitize_outgoing_answer(answer: str) -> str:
    """
    Defensive post-check: if the generated answer text accidentally contains
    a hard conclusion (declared fraud, or a final accept/reject decision),
    soften it. This is a safety net in addition to careful prompt/template
    construction in copilot_service.
    """
    lowered = answer.lower()
    for phrase in _UNSUPPORTED_CONCLUSION_PHRASES:
        if phrase in lowered:
            return (
                "I can summarize the supporting evidence and risk indicators, but I can't declare fraud or "
                "make the final accept/reject decision — that determination is reserved for the human "
                "investigator. " + answer
            )
    return answer
