"""Redis wakeup queue; Postgres remains authoritative when Redis loses data."""

from __future__ import annotations

from redis import Redis

from app.core import telemetry
from app.core.metrics import emit_metric

QUEUE_KEY = "hcg:jobs:ready"
IDLE_RECEIVE_TIMEOUT_S = 15
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
    def from_url(cls, url: str, *, socket_timeout: int = 3) -> JobQueue:
        return cls(
            Redis.from_url(
                url,
                socket_connect_timeout=3,
                socket_timeout=socket_timeout,
            )
        )

    def enqueue(self, job_id: str, *, force: bool = False) -> None:
        marker = f"hcg:jobs:queued:{job_id}"
        with telemetry.safe_span("redis.queue_enqueue"):
            if force:
                with self.redis.pipeline() as pipeline:
                    pipeline.set(marker, "1", ex=60)
                    pipeline.lpush(QUEUE_KEY, job_id)
                    pipeline.execute()
                return
            self.redis.eval(_ENQUEUE_SCRIPT, 2, marker, QUEUE_KEY, job_id)

    def receive(self, timeout: int = IDLE_RECEIVE_TIMEOUT_S) -> str | None:
        with telemetry.safe_span("redis.queue_receive"):
            result = self.redis.brpop(QUEUE_KEY, timeout=timeout)
        return result[1].decode("ascii") if result is not None else None

    def emit_depth(self) -> int:
        """Sample Redis's ready-list depth for the worker's periodic metrics."""
        with telemetry.safe_span("redis.queue_depth"):
            depth = int(self.redis.llen(QUEUE_KEY))
        emit_metric("queue_depth", depth, queue="jobs")
        return depth

    def close(self) -> None:
        self.redis.close()
