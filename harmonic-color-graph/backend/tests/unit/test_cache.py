"""F28 cache versioning, fallback, and cross-instance rate counters."""

from redis.exceptions import ConnectionError as RedisConnectionError

from app.core.cache import RateLimiter, VersionedCache, cache_key


class FakeRedis:
    def __init__(self):
        self.values = {}
        self.counters = {}
        self.fail = False

    def get(self, key):
        if self.fail:
            raise RedisConnectionError("down")
        return self.values.get(key)

    def setex(self, key, time, value):
        if self.fail:
            raise RedisConnectionError("down")
        self.values[key] = value

    def eval(self, _script, _numkeys, key, window_s):
        if self.fail:
            raise RedisConnectionError("down")
        self.counters[key] = self.counters.get(key, 0) + 1
        return [self.counters[key], window_s]


def test_version_change_cannot_read_stale_graph_payload():
    redis = FakeRedis()
    first = VersionedCache(redis)
    second = VersionedCache(redis)
    assert first.get_or_compute(
        version="cv-a",
        kind="graph:neighbors",
        parts={"id": "M:I"},
        ttl_s=30,
        producer=lambda: {"nodes": ["old"]},
    ) == {"nodes": ["old"]}
    assert second.get_or_compute(
        version="cv-a",
        kind="graph:neighbors",
        parts={"id": "M:I"},
        ttl_s=30,
        producer=lambda: {"nodes": ["wrong"]},
    ) == {"nodes": ["old"]}
    assert second.metrics.l2_hits == 1
    assert second.get_or_compute(
        version="cv-b",
        kind="graph:neighbors",
        parts={"id": "M:I"},
        ttl_s=30,
        producer=lambda: {"nodes": ["new"]},
    ) == {"nodes": ["new"]}
    assert cache_key("cv-a", "graph:neighbors", {"id": "M:I"}) != cache_key(
        "cv-b", "graph:neighbors", {"id": "M:I"}
    )


def test_redis_outage_bypasses_cache_and_policy_controls_limits():
    redis = FakeRedis()
    redis.fail = True
    cache = VersionedCache(redis)
    assert cache.get_or_compute(
        version="cv-a",
        kind="graph:path",
        parts=["M:I", "M:V"],
        ttl_s=10,
        producer=lambda: {"paths": [1]},
    ) == {"paths": [1]}
    assert cache.metrics.redis_errors == 1
    assert cache.metrics.write_errors == 1
    limiter = RateLimiter(redis)
    assert limiter.check(
        scope="analysis", subject="one", limit=1, window_s=60, fail_mode="open"
    ).allowed
    assert not limiter.check(
        scope="ai", subject="one", limit=1, window_s=60, fail_mode="closed"
    ).allowed


def test_two_instances_share_redis_rate_limit_counter():
    redis = FakeRedis()
    one, two = RateLimiter(redis), RateLimiter(redis)
    assert one.check(scope="ai", subject="ip:one", limit=1, window_s=60, fail_mode="closed").allowed
    decision = two.check(scope="ai", subject="ip:one", limit=1, window_s=60, fail_mode="closed")
    assert not decision.allowed
    assert decision.count == 2
    assert decision.retry_after_s == 60


def test_local_cache_ttl_expires(monkeypatch):
    now = [100.0]
    monkeypatch.setattr("app.core.cache.time.monotonic", lambda: now[0])
    cache = VersionedCache()
    calls = [0]

    def produce():
        calls[0] += 1
        return {"value": calls[0]}

    params = {"version": "cv-a", "kind": "graph:neighbors", "parts": ["M:I"], "ttl_s": 2}
    assert cache.get_or_compute(**params, producer=produce) == {"value": 1}
    now[0] = 101.0
    assert cache.get_or_compute(**params, producer=produce) == {"value": 1}
    now[0] = 102.0
    assert cache.get_or_compute(**params, producer=produce) == {"value": 2}
