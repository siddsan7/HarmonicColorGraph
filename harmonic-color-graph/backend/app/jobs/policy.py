"""Centralized transient-failure classification for bounded job retries."""

from __future__ import annotations

import httpx
from psycopg import OperationalError
from redis.exceptions import RedisError

RETRYABLE_HTTP_STATUSES = {429, 502, 503, 504}


def is_retryable(exc: Exception) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in RETRYABLE_HTTP_STATUSES
    return isinstance(
        exc,
        (
            TimeoutError,
            ConnectionError,
            OSError,
            RedisError,
            OperationalError,
            httpx.TimeoutException,
            httpx.NetworkError,
        ),
    )
