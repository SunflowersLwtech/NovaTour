"""Lightweight resilience utilities for NovaTour tools.

Sources:
- retry_api_call: iMean_Piper_Prod google_search_tool.py + syntour1018 error_handler.py
- safe_json_loads: syntour1018 helpers.py
- is_recoverable: syntour1018 error_handler.py
- timed_log: iMean_Piper_Prod tool_manager.py
"""

import json
import logging
import re
import time
from contextlib import contextmanager
from typing import Any, Tuple, Type

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import settings

# Default HTTP exceptions worth retrying
_RETRYABLE_HTTP = (httpx.TimeoutException, httpx.ConnectError)


def retry_api_call(
    retry_on: Tuple[Type[BaseException], ...] = _RETRYABLE_HTTP,
):
    """Decorator: retry a function on transient errors with exponential backoff.

    Non-retryable HTTP errors (4xx except 429) are raised immediately.
    """

    def _should_retry(exc: BaseException) -> bool:
        if isinstance(exc, httpx.HTTPStatusError):
            code = exc.response.status_code
            # Retry 429 (rate limit) and 5xx; skip other 4xx
            return code == 429 or code >= 500
        return isinstance(exc, retry_on)

    return retry(
        retry=retry_if_exception_type(retry_on) | retry_if_exception_type(httpx.HTTPStatusError),
        stop=stop_after_attempt(settings.tool_retry_attempts),
        wait=wait_exponential(
            multiplier=1,
            min=settings.tool_retry_min_wait,
            max=settings.tool_retry_max_wait,
        ),
        reraise=True,
        before_sleep=lambda rs: logging.getLogger(__name__).warning(
            f"Retry {rs.attempt_number}/{settings.tool_retry_attempts} "
            f"after {rs.outcome.exception().__class__.__name__}"
        ),
    )


def safe_json_loads(text: str, default: Any = None) -> Any:
    """Parse JSON with fallback strategies: direct → strip markdown fence → brace extraction."""
    text = text.strip()

    # 1) Direct parse
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        pass

    # 2) Strip markdown code fences
    if text.startswith("```"):
        lines = text.split("\n")
        inner = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        try:
            return json.loads(inner.strip())
        except (json.JSONDecodeError, TypeError):
            pass

    # 3) Extract first { ... } block
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            return json.loads(match.group())
        except (json.JSONDecodeError, TypeError):
            pass

    return default


def is_recoverable(exc: BaseException) -> bool:
    """Classify whether an error is worth retrying / falling back from."""
    msg = str(exc).lower()
    # Non-recoverable keywords
    for kw in ("auth", "permission", "forbidden", "401", "403", "invalid_api_key"):
        if kw in msg:
            return False
    # Recoverable keywords
    for kw in ("timeout", "timed out", "connect", "rate_limit", "429", "throttl", "502", "503", "504"):
        if kw in msg:
            return True
    # Default: treat unknown errors as recoverable (safer for voice UX)
    return True


@contextmanager
def timed_log(logger: logging.Logger, operation: str, session_id: str = ""):
    """Context manager that logs operation name + elapsed time."""
    start = time.time()
    try:
        yield
    finally:
        elapsed = time.time() - start
        sid = f" session={session_id}" if session_id else ""
        logger.info(f"{operation} completed in {elapsed:.3f}s{sid}")
