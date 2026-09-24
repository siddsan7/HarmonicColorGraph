"""Durable worker process with Postgres reconciliation and Redis wakeups."""

import logging
import signal
import threading

from app.core.config import get_settings
from app.db.session import create_session_factory
from app.jobs.queue import JobQueue
from app.jobs.worker_runtime import JobWorker
from app.runtime_check import check_dependencies

logger = logging.getLogger(__name__)
stop_event = threading.Event()


def _stop(_signum: int, _frame: object) -> None:
    stop_event.set()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    check_dependencies()
    settings = get_settings()
    if not settings.redis_url:
        raise RuntimeError("REDIS_URL is required for the job worker")
    queue = JobQueue.from_url(settings.redis_url)
    try:
        logger.info("Worker connected; reconciling durable queued jobs")
        JobWorker(create_session_factory(), queue, settings).run_forever(stop_event.is_set)
    finally:
        queue.close()


if __name__ == "__main__":
    main()
