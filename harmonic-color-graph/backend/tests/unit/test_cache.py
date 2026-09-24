"""F28 cache versioning, fallback, and cross-instance rate counters."""

import json

from redis.exceptions import ConnectionError as RedisConnectionError

from app.core.cache import RateLimiter, VersionedCache, cache_key
from app.jobs.queue import JobQueue


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

    def llen(self, key):
        return len(self.values.get(key, []))


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


def test_cache_and_rate_metrics_emit_structured_events_without_cache_keys(caplog):
    redis = FakeRedis()
    first, second = VersionedCache(redis), VersionedCache(redis)
    params = {
        "version": "cv-a",
        "kind": "graph:neighbors",
        "parts": {"private": "do-not-log"},
        "ttl_s": 30,
    }
    assert first.get_or_compute(**params, producer=lambda: {"nodes": ["M:I"]}) == {"nodes": ["M:I"]}
    assert first.get_or_compute(**params, producer=lambda: None) == {"nodes": ["M:I"]}
    assert second.get_or_compute(**params, producer=lambda: None) == {"nodes": ["M:I"]}
    limiter = RateLimiter(redis)
    limiter.check(scope="graph", subject="secret-ip", limit=1, window_s=60, fail_mode="open")
    assert not limiter.check(
        scope="graph", subject="secret-ip", limit=1, window_s=60, fail_mode="open"
    ).allowed

    events = [
        json.loads(record.message) for record in caplog.records if record.name == "hcg.metrics"
    ]
    names = [event["metric"] for event in events]
    assert names.count("cache_hits") == 2
    assert names.count("cache_misses") == 1
    assert names.count("cache_hit_rate") == 3
    assert "redis_latency_ms" in names
    assert names.count("rate_limit_hits") == 1
    assert "do-not-log" not in caplog.text
    assert "secret-ip" not in caplog.text


def test_queue_depth_metric_samples_redis_ready_list(caplog):
    redis = FakeRedis()
    redis.values["hcg:jobs:ready"] = ["a", "b"]
    assert JobQueue(redis).emit_depth() == 2
    events = [
        json.loads(record.message) for record in caplog.records if record.name == "hcg.metrics"
    ]
    assert events == [{"metric": "queue_depth", "queue": "jobs", "value": 2}]
