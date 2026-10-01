"""Durable worker process with Postgres reconciliation and Redis wakeups."""

import logging
import signal
import threading

from app.core.config import get_settings
from app.core.telemetry import configure_telemetry
from app.db.session import create_session_factory
from app.jobs.queue import IDLE_RECEIVE_TIMEOUT_S, JobQueue
from app.jobs.worker_runtime import JobWorker
from app.runtime_check import check_dependencies

logger = logging.getLogger(__name__)
stop_event = threading.Event()


def _stop(_signum: int, _frame: object) -> None:
    stop_event.set()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    configure_telemetry()
    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    check_dependencies()
    settings = get_settings()
    if not settings.redis_url:
        raise RuntimeError("REDIS_URL is required for the job worker")
    # The worker's blocking BRPOP needs a longer timeout than API enqueue calls.
    queue = JobQueue.from_url(settings.redis_url, socket_timeout=IDLE_RECEIVE_TIMEOUT_S + 5)
    try:
        logger.info("Worker connected; reconciling durable queued jobs")
        JobWorker(create_session_factory(), queue, settings).run_forever(stop_event.is_set)
    finally:
        queue.close()


if __name__ == "__main__":
    main()
