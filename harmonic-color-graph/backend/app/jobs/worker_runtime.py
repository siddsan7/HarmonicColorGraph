"""Single-process worker. The DB ledger recovers queued work after Redis loss."""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from uuid import uuid4

from pydantic import ValidationError
from redis.exceptions import RedisError
from sqlalchemy.orm import Session

from app.core.config import AppSettings
from app.jobs.handlers import JobTypeUnavailableError, run_job
from app.jobs.policy import is_retryable
from app.jobs.queue import JobQueue
from app.jobs.repository import JobRepository, parse_job_id

logger = logging.getLogger(__name__)


class JobWorker:
    def __init__(
        self,
        session_factory: Callable[[], Session],
        queue: JobQueue,
        settings: AppSettings,
        worker_id: str | None = None,
    ):
        self.session_factory = session_factory
        self.queue = queue
        self.settings = settings
        self.worker_id = worker_id or str(uuid4())

    def reconcile(self, *, force: bool = False) -> int:
        with self.session_factory() as session:
            repository = JobRepository(session)
            expired = repository.recover_expired()
            queued_ids = repository.queued_ids()
        if expired:
            logger.warning("Recovered %d expired worker leases", expired)
        for job_id in queued_ids:
            self.queue.enqueue(job_id, force=force)
        return len(queued_ids)

    def process_one(self, timeout: int = 5) -> bool:
        raw_id = self.queue.receive(timeout=timeout)
        if raw_id is None:
            return False
        try:
            job_id = parse_job_id(raw_id)
        except ValueError:
            logger.warning("Discarded malformed queue job ID")
            return False

        with self.session_factory() as session:
            job = JobRepository(session).claim(job_id, self.worker_id)
        if job is None:
            return False  # Duplicate wakeup, cancelled, or already claimed.

        heartbeat_stop = threading.Event()

        def renew_until_done() -> None:
            while not heartbeat_stop.wait(30):
                try:
                    with self.session_factory() as session:
                        if not JobRepository(session).renew_lease(job_id, self.worker_id):
                            return
                except Exception:
                    logger.exception("Lease renewal failed for job %s", job_id)

        heartbeat = threading.Thread(target=renew_until_done, daemon=True)
        heartbeat.start()

        def progress(value: float, stage: str, processed: int | None, total: int | None) -> None:
            with self.session_factory() as session:
                JobRepository(session).update_progress(
                    job_id,
                    self.worker_id,
                    progress=value,
                    stage=stage,
                    processed=processed,
                    total=total,
                )

        try:
            result = run_job(job["type"], job["payload"], self.settings, progress)
        except (ValidationError, JobTypeUnavailableError, FileNotFoundError, ValueError) as exc:
            logger.warning("Job %s failed validation: %s", job_id, type(exc).__name__)
            with self.session_factory() as session:
                JobRepository(session).fail(job_id, self.worker_id, "invalid_job", str(exc))
        except Exception as exc:
            retryable = is_retryable(exc)
            logger.exception("Job %s failed (retryable=%s)", job_id, retryable)
            with self.session_factory() as session:
                JobRepository(session).fail(
                    job_id,
                    self.worker_id,
                    "temporary_failure" if retryable else "job_failed",
                    "Job execution failed; inspect worker logs.",
                    retryable=retryable,
                )
        else:
            with self.session_factory() as session:
                JobRepository(session).complete(job_id, self.worker_id, result)
        finally:
            heartbeat_stop.set()
            heartbeat.join(timeout=5)
        return True

    def run_forever(self, should_stop: Callable[[], bool]) -> None:
        recovered = False
        next_reconcile = 0.0
        while not should_stop():
            try:
                now = time.monotonic()
                if now >= next_reconcile:
                    count = self.reconcile(force=not recovered)
                    self.queue.emit_depth()
                    if count:
                        logger.info("Reconciled %d queued jobs", count)
                    recovered = True
                    next_reconcile = now + 30
                self.process_one(timeout=5)
            except RedisError:
                logger.warning("Redis queue unavailable; retrying")
                recovered = False
                time.sleep(3)
            except Exception:
                logger.exception("Worker loop failed; retrying")
                time.sleep(3)
