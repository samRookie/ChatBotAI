"""Centralized resilience utilities for Gemini API interactions.

Provides bounded exponential backoff with jitter, structured error classification
(retryable vs non-retryable vs quota-exhausted), before-sleep warning observability,
and model failover eligibility gating.
"""

import logging
from typing import Any, Callable

from google.genai import errors as genai_errors
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_random_exponential,
)

logger = logging.getLogger(__name__)

# Non-transient quota phrases in 429 error messages that cannot recover within seconds
_QUOTA_EXHAUSTED_PHRASES = (
    "daily quota",
    "per day",
    "quota exceeded for the day",
    "free tier per day",
    "daily limit",
    "quota_exceeded_daily",
)


def is_quota_exhausted(exc: BaseException) -> bool:
    """True if exception indicates non-transient daily/project quota exhaustion."""
    if not isinstance(exc, genai_errors.APIError):
        return False

    code = getattr(exc, "code", None)
    if code != 429:
        return False

    msg = str(getattr(exc, "message", str(exc))).lower()
    return any(phrase in msg for phrase in _QUOTA_EXHAUSTED_PHRASES)


def is_retryable_error(exc: BaseException) -> bool:
    """Classify whether an exception is retryable with bounded backoff.

    Retryable:
    - 503 (Service Unavailable / Capacity Overload)
    - 429 transient rate-limit / request burst (unless clearly daily quota exhaustion)
    - Server-side transient errors

    Non-retryable (fail fast):
    - 400 Bad Request / malformed payload
    - 401 / 403 Authentication / Permission errors
    - 404 Model Not Found
    - 429 non-transient daily quota exhaustion
    - Configuration or runtime errors
    """
    if isinstance(exc, (RuntimeError, ValueError, TypeError)):
        return False

    if isinstance(exc, genai_errors.APIError):
        code = getattr(exc, "code", None)
        # 503 is always retryable
        if code == 503:
            return True
        # 429: retry if transient, fail fast if daily quota exhausted
        if code == 429:
            return not is_quota_exhausted(exc)
        # 400, 401, 403, 404, etc. are non-retryable client errors
        if code in (400, 401, 403, 404):
            return False
        # Other 5xx server errors are retryable
        if isinstance(exc, genai_errors.ServerError) or (isinstance(code, int) and code >= 500):
            return True
        return False

    # Check for transient network/connection issues
    exc_name = type(exc).__name__.lower()
    if any(k in exc_name for k in ("timeout", "connecterror", "connectionreset", "networkerror")):
        return True

    return False


def is_failover_eligible(exc: BaseException) -> bool:
    """Determine whether an exhausted error is eligible for single model failover.

    Eligible:
    - 503 service-capacity failure / server overload
    - 429 quota exhaustion / rate-limit exhaustion
    - Server-side 5xx errors
    Never fail over for auth (401/403), malformed request (400), 404, or application bugs.
    """
    if isinstance(exc, genai_errors.APIError):
        code = getattr(exc, "code", None)
        if code in (429, 503) or isinstance(exc, genai_errors.ServerError):
            return True
    return False


def log_retry_warning(retry_state: Any, operation: str, model_name: str) -> None:
    """Before-sleep callback logging structured metadata without sensitive data."""
    attempt = retry_state.attempt_number
    wait_time = getattr(retry_state.next_action, "sleep", 0.0) or 0.0
    exc = retry_state.outcome.exception() if retry_state.outcome else None

    status = getattr(exc, "code", type(exc).__name__ if exc else "unknown")
    logger.warning(
        "Gemini request retry scheduled: operation=%s model=%s attempt=%s status=%s wait=%.2fs",
        operation,
        model_name,
        attempt,
        status,
        wait_time,
    )


def build_retry_decorator(
    operation: str,
    model_name: str,
    max_attempts: int = 5,
    min_wait: float = 2.0,
    max_wait: float = 10.0,
    wait_strategy: Any = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Create a Tenacity retry decorator with jittered backoff and observability logging."""
    actual_wait = (
        wait_strategy
        if wait_strategy is not None
        else wait_random_exponential(min=min_wait, max=max_wait)
    )

    return retry(
        retry=retry_if_exception(is_retryable_error),
        wait=actual_wait,
        stop=stop_after_attempt(max_attempts),
        before_sleep=lambda rs: log_retry_warning(rs, operation=operation, model_name=model_name),
        reraise=True,
    )
