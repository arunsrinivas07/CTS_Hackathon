"""
tool_helpers.py
===============

Shared utility functions, decorators, and helper routines across tools.
"""

from __future__ import annotations

import functools
import logging
import time
from typing import Any, Callable, Dict, Optional, TypeVar
from schemas.tool import ToolErrorResponse

# Standard tools logger
logger = logging.getLogger("tools")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

F = TypeVar("F", bound=Callable[..., Any])


def timed(func: F) -> F:
    """Decorator that logs execution time for tools and services."""
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start = time.perf_counter()
        try:
            return func(*args, **kwargs)
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.debug("%s took %.2fms", func.__qualname__, elapsed_ms)

    return wrapper  # type: ignore[return-value]


def format_tool_error(
    error_code: str,
    message: str,
    details: Optional[Dict[str, Any]] = None,
) -> ToolErrorResponse:
    """Build a standard structured ToolErrorResponse."""
    return ToolErrorResponse(
        status="error",
        error_code=error_code,
        message=message,
        details=details or {},
    )


def normalize_text_input(text: str) -> str:
    """Normalize text input: trim whitespace, strip extraneous control characters."""
    if not text:
        return ""
    return " ".join(text.split()).strip()
