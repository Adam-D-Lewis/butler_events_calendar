"""Retry utilities for Google Calendar API operations."""

import socket

from googleapiclient.errors import HttpError
from loguru import logger
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)


def log_retry_attempt(retry_state):
    """Log retry attempts for debugging."""
    logger.warning(
        f"Retry attempt {retry_state.attempt_number} after error: "
        f"{retry_state.outcome.exception()}"
    )


# Retry decorator for Google Calendar batch operations
# Retries on timeout, connection, and transient HTTP errors (5xx)
gcal_retry = retry(
    retry=retry_if_exception_type(
        (
            TimeoutError,
            socket.timeout,
            ConnectionError,
            OSError,  # Covers "cannot read from timed out object"
        )
    )
    | retry_if_exception_type(HttpError),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    before_sleep=before_sleep_log(logger, log_level="WARNING"),
    reraise=True,
)


def is_retryable_http_error(exception: Exception) -> bool:
    """Check if an HttpError is retryable (5xx errors or rate limiting)."""
    if isinstance(exception, HttpError):
        status = exception.resp.status
        # Retry on 5xx server errors and 429 rate limiting
        return status >= 500 or status == 429
    return False
