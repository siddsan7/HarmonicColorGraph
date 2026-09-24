"""F28 version-scoped L1/L2 cache and distributed fixed-window limits.

Only reconstructable public data belongs here. Durable truth remains in
Postgres. Redis failures bypass reads; callers choose a rate-limit outage
policy explicitly for each endpoint.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass
from threading import Lock
from typing import Any, Literal, Protocol, TypeVar

from redis import Redis
from redis.exceptions import RedisError

from app.core.config import get_settings

logger = logging.getLogger(__name__)
T = TypeVar("T")


class RedisClient(Protocol):
    def get(self, key: str) -> bytes | str | None: ...
    def setex(self, key: str, time: int, value: str) -> Any: ...
    def eval(self, script: str, numkeys: int, *keys_and_args: Any) -> Any: ...


def redis_client() -> Redis | None:
    url = get_settings().redis_url
    if not url:
        return None
    return Redis.from_url(url, socket_connect_timeout=0.5, socket_timeout=0.5)


def cache_key(version: str, kind: str, parts: Any) -> str:
    if not version or not kind:
        raise ValueError("Cache version and kind are required")
    canonical = json.dumps(parts, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:32]
    return f"hcg:{version}:{kind}:{digest}"


@dataclass
class CacheMetrics:
    l1_hits: int = 0
    l2_hits: int = 0
    misses: int = 0
    redis_errors: int = 0
    write_errors: int = 0

    @property
    def hit_rate(self) -> float:
        total = self.l1_hits + self.l2_hits + self.misses
        return (self.l1_hits + self.l2_hits) / total if total else 0.0


class VersionedCache:
    def __init__(self, redis: RedisClient | None = None, *, max_local: int = 256):
        self.redis = redis
        self.max_local = max_local
        self.metrics = CacheMetrics()
        self._local: OrderedDict[str, tuple[float, Any]] = OrderedDict()
        self._lock = Lock()

    def _local_get(self, key: str) -> Any | None:
        with self._lock:
            entry = self._local.get(key)
            if entry is None:
                return None
            deadline, value = entry
            if time.monotonic() >= deadline:
                del self._local[key]
                return None
            self._local.move_to_end(key)
            return value

    def _local_put(self, key: str, value: Any, ttl_s: int) -> None:
        with self._lock:
            self._local[key] = (time.monotonic() + ttl_s, value)
            self._local.move_to_end(key)
            while len(self._local) > self.max_local:
                self._local.popitem(last=False)

    def get_or_compute(
        self,
        *,
        version: str,
        kind: str,
        parts: Any,
        ttl_s: int,
        producer: Callable[[], T],
    ) -> T:
        if ttl_s <= 0:
            raise ValueError("ttl_s must be positive")
        key = cache_key(version, kind, parts)
        local = self._local_get(key)
        if local is not None:
            self.metrics.l1_hits += 1
            return local
        if self.redis is not None:
            try:
                raw = self.redis.get(key)
                if raw is not None:
                    value = json.loads(raw)
                    self._local_put(key, value, ttl_s)
                    self.metrics.l2_hits += 1
                    return value
            except (RedisError, OSError, ValueError, TypeError):
                self.metrics.redis_errors += 1
                logger.warning("Redis cache read failed", extra={"error_category": "redis_read"})
        self.metrics.misses += 1
        value = producer()
        self._local_put(key, value, ttl_s)
        if self.redis is not None:
            try:
                self.redis.setex(key, ttl_s, json.dumps(value, ensure_ascii=False))
            except (RedisError, OSError, ValueError, TypeError):
                self.metrics.write_errors += 1
                logger.warning("Redis cache write failed", extra={"error_category": "redis_write"})
        return value


_FIXED_WINDOW_SCRIPT = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]) end
local remaining = redis.call('TTL', KEYS[1])
return {count, remaining}
"""


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    count: int
    remaining: int
    retry_after_s: int
    degraded: bool = False


class RateLimiter:
    def __init__(self, redis: RedisClient | None):
        self.redis = redis
        self.limit_hits = 0
        self.redis_errors = 0

    def check(
        self,
        *,
        scope: str,
        subject: str,
        limit: int,
        window_s: int,
        fail_mode: Literal["open", "closed"],
    ) -> RateLimitDecision:
        if not scope or not subject or limit <= 0 or window_s <= 0:
            raise ValueError("A scope, subject, positive limit, and positive window are required")
        subject_hash = hashlib.sha256(subject.encode("utf-8")).hexdigest()[:32]
        window = int(time.time()) // window_s
        key = f"hcg:rate:{scope}:{subject_hash}:{window}"
        try:
            if self.redis is None:
                raise ConnectionError("Redis is not configured")
            count, ttl = self.redis.eval(_FIXED_WINDOW_SCRIPT, 1, key, window_s)
            count, ttl = int(count), max(0, int(ttl))
        except (RedisError, OSError, ConnectionError, ValueError, TypeError):
            self.redis_errors += 1
            logger.warning("Redis rate limit unavailable", extra={"error_category": "redis_rate"})
            return RateLimitDecision(fail_mode == "open", 0, 0, 0, degraded=True)
        allowed = count <= limit
        if not allowed:
            self.limit_hits += 1
        return RateLimitDecision(allowed, count, max(0, limit - count), ttl if not allowed else 0)
