"""The idle worker must fit a metered Redis service's free command budget."""

from math import ceil

from app.core.config import AppSettings
from app.jobs.queue import QUEUE_KEY, JobQueue
from app.jobs.worker_runtime import JobWorker


def test_idle_worker_blocks_long_enough_for_free_tier_and_keeps_depth_metric(monkeypatch):
    class RedisStub:
        def __init__(self):
            self.receives = []
            self.depth_samples = 0

        def brpop(self, key, timeout):
            self.receives.append((key, timeout))
            return None

        def llen(self, key):
            assert key == QUEUE_KEY
            self.depth_samples += 1
            return 0

    redis = RedisStub()
    worker = JobWorker(lambda: None, JobQueue(redis), AppSettings())
    monkeypatch.setattr(worker, "reconcile", lambda *, force: 0)
    worker.run_forever(lambda: bool(redis.receives))

    assert redis.receives[0][0] == QUEUE_KEY
    assert redis.depth_samples == 1
    receive_interval = redis.receives[0][1]
    month_seconds = 31 * 24 * 60 * 60
    # One idle BRPOP and one 30-second LLEN sample per cycle; leave room for API traffic.
    assert ceil(month_seconds / receive_interval) + ceil(month_seconds / 30) < 300_000


def test_queue_socket_timeout_outlives_blocking_receive(monkeypatch):
    captured = {}

    def from_url(url, **kwargs):
        captured.update(kwargs)
        return object()

    monkeypatch.setattr("app.jobs.queue.Redis.from_url", from_url)
    JobQueue.from_url("rediss://unused.example:6379")
    assert captured["socket_timeout"] > 15
