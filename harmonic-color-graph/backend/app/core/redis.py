"""Shared Redis connectivity; queue/cache behavior arrives in F27/F28."""

from redis import Redis

from app.core.config import get_settings


def ping_redis() -> None:
    url = get_settings().redis_url
    if not url:
        raise RuntimeError("REDIS_URL is not configured")
    client = Redis.from_url(url, socket_connect_timeout=3, socket_timeout=3)
    try:
        if not client.ping():
            raise RuntimeError("Redis did not answer PING")
    finally:
        client.close()
