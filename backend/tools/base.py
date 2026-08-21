"""
Tool base interface + the controlled registry.

SECURITY NOTE: the LLM only ever *proposes* a tool name (a string). This
module is the enforcement point -- we never call anything the LLM says
unless it is literally a key in TOOL_REGISTRY. This prevents arbitrary
function execution regardless of what the model outputs.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from schemas.tool import ToolOutput


class BaseTool(ABC):
    name: str
    description: str

    @abstractmethod
    def run(self, **kwargs: Any) -> ToolOutput:
        """Execute the tool synchronously and return a normalized ToolOutput.

        Implementations must never raise for expected "no data" cases --
        they should return status=NO_EVIDENCE_FOUND instead. Only truly
        unexpected failures (timeouts, exceptions) should propagate, and
        even then tool_executor.py catches them and records TOOL_FAILURE.
        """
        raise NotImplementedError


# Populated in tools/__init__.py once concrete tool instances exist.
# Kept as a plain dict (not a class) per the spec: "Use a controlled
# registry such as TOOL_REGISTRY = {...}".
TOOL_REGISTRY: dict[str, BaseTool] = {}


def register_tool(tool: BaseTool) -> None:
    TOOL_REGISTRY[tool.name] = tool


def is_registered(tool_name: str) -> bool:
    return tool_name in TOOL_REGISTRY


def get_tool(tool_name: str) -> BaseTool:
    if not is_registered(tool_name):
        raise KeyError(f"Tool '{tool_name}' is not in TOOL_REGISTRY")
    return TOOL_REGISTRY[tool_name]
