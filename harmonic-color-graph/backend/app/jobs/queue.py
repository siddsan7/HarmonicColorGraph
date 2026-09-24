"""Redis wakeup queue; Postgres remains authoritative when Redis loses data."""

from __future__ import annotations

from redis import Redis

from app.core.metrics import emit_metric

QUEUE_KEY = "hcg:jobs:ready"
_ENQUEUE_SCRIPT = """
if redis.call('SET', KEYS[1], '1', 'NX', 'EX', 60) then
  redis.call('LPUSH', KEYS[2], ARGV[1])
  return 1
end
return 0
"""


class JobQueue:
    def __init__(self, redis: Redis):
        self.redis = redis

    @classmethod
    def from_url(cls, url: str) -> JobQueue:
        return cls(Redis.from_url(url, socket_connect_timeout=3, socket_timeout=3))

    def enqueue(self, job_id: str, *, force: bool = False) -> None:
        marker = f"hcg:jobs:queued:{job_id}"
        if force:
            with self.redis.pipeline() as pipeline:
                pipeline.set(marker, "1", ex=60)
                pipeline.lpush(QUEUE_KEY, job_id)
                pipeline.execute()
            return
        self.redis.eval(_ENQUEUE_SCRIPT, 2, marker, QUEUE_KEY, job_id)

    def receive(self, timeout: int = 5) -> str | None:
        result = self.redis.brpop(QUEUE_KEY, timeout=timeout)
        return result[1].decode("ascii") if result is not None else None

    def emit_depth(self) -> int:
        """Sample Redis's ready-list depth for the worker's periodic metrics."""
        depth = int(self.redis.llen(QUEUE_KEY))
        emit_metric("queue_depth", depth, queue="jobs")
        return depth

    def close(self) -> None:
        self.redis.close()
