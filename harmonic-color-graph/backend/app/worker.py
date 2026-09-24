"""F09 worker bootstrap; F27 replaces the heartbeat with queue consumption."""

import logging
import signal
import threading

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
    logger.info("Worker bootstrap connected to Postgres and Redis; job processing begins in F27")
    while not stop_event.wait(15):
        try:
            check_dependencies()
        except Exception:
            logger.exception("Worker dependency check failed")
            raise


if __name__ == "__main__":
    main()
