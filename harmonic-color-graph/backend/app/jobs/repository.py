"""Postgres job ledger. Redis messages never carry payloads or durable state."""

from __future__ import annotations

import hashlib
import json
import random
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session


class JobRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(
        self, kind: str, payload: dict, idempotency_key: str | None = None
    ) -> tuple[dict, bool]:
        digest = hashlib.sha256(
            json.dumps({"type": kind, "payload": payload}, sort_keys=True).encode()
        ).hexdigest()
        if idempotency_key:
            self.session.execute(
                text("select pg_advisory_xact_lock(hashtext(:key))"), {"key": idempotency_key}
            )
            prior = (
                self.session.execute(
                    text(
                        """select operation, request_hash, job_id, expires_at
                       from hcg.idempotency_keys where key = :key for update"""
                    ),
                    {"key": idempotency_key},
                )
                .mappings()
                .first()
            )
            if prior and prior["expires_at"] > datetime.now(UTC):
                if prior["operation"] != kind or prior["request_hash"] != digest:
                    self.session.rollback()
                    raise IdempotencyConflictError(
                        "Idempotency key was used with a different request"
                    )
                job = self.get(str(prior["job_id"]))
                self.session.commit()
                return job, False  # type: ignore[return-value]
            if prior:
                self.session.execute(
                    text("delete from hcg.idempotency_keys where key = :key"),
                    {"key": idempotency_key},
                )
        row = (
            self.session.execute(
                text(
                    """insert into hcg.jobs (type, payload, request_hash)
                   values (:kind, cast(:payload as jsonb), :digest)
                   returning id"""
                ),
                {"kind": kind, "payload": json.dumps(payload), "digest": digest},
            )
            .mappings()
            .one()
        )
        self._event(str(row["id"]), "queued", "queued", 0)
        if idempotency_key:
            self.session.execute(
                text(
                    """insert into hcg.idempotency_keys
                       (key, operation, request_hash, job_id)
                       values (:key, :kind, :digest, :job_id)"""
                ),
                {"key": idempotency_key, "kind": kind, "digest": digest, "job_id": row["id"]},
            )
        self.session.commit()
        return self.get(str(row["id"])), True  # type: ignore[return-value]

    def _event(
        self,
        job_id: str,
        status: str,
        stage: str,
        progress: float,
        processed: int | None = None,
        total: int | None = None,
    ) -> None:
        self.session.execute(
            text(
                """insert into hcg.job_events
                   (job_id, status, stage, progress, processed, total)
                   values (cast(:job_id as uuid), :status, :stage,
                           :progress, :processed, :total)"""
            ),
            {
                "job_id": job_id,
                "status": status,
                "stage": stage,
                "progress": progress,
                "processed": processed,
                "total": total,
            },
        )

    def events(self, job_id: str, limit: int = 100) -> list[dict]:
        rows = self.session.execute(
            text(
                """select id, status, stage, progress, processed, total, created_at
                   from hcg.job_events where job_id = cast(:job_id as uuid)
                   order by id desc limit :limit"""
            ),
            {"job_id": job_id, "limit": limit},
        ).mappings()
        return [dict(row) for row in reversed(list(rows))]

    def get(self, job_id: str) -> dict | None:
        row = (
            self.session.execute(
                text(
                    """select id, type, status, payload, result, progress, stage,
                          processed, total, attempt, max_attempts, created_at,
                          queued_at, started_at, completed_at, failed_at,
                          last_error_code, last_error_message, worker_id,
                          available_at, lease_expires_at
                   from hcg.jobs where id = cast(:job_id as uuid)"""
                ),
                {"job_id": job_id},
            )
            .mappings()
            .first()
        )
        if row is None:
            return None
        result = dict(row)
        result["id"] = str(result["id"])
        return result

    def queued_ids(self, limit: int = 1000) -> list[str]:
        rows = self.session.execute(
            text(
                """select id from hcg.jobs
                   where status in ('queued', 'retrying') and available_at <= now()
                   order by available_at, created_at limit :limit"""
            ),
            {"limit": limit},
        ).scalars()
        return [str(job_id) for job_id in rows]

    def claim(self, job_id: str, worker_id: str) -> dict | None:
        row = (
            self.session.execute(
                text(
                    """update hcg.jobs
                   set status = 'running', started_at = now(),
                       attempt = attempt + 1, worker_id = :worker_id,
                       stage = 'starting', lease_expires_at = now() + interval '90 seconds'
                   where id = cast(:job_id as uuid)
                     and status in ('queued', 'retrying') and available_at <= now()
                   returning id"""
                ),
                {"job_id": job_id, "worker_id": worker_id},
            )
            .mappings()
            .first()
        )
        if row is not None:
            self._event(job_id, "running", "starting", 0)
        self.session.commit()
        return self.get(str(row["id"])) if row is not None else None

    def update_progress(
        self,
        job_id: str,
        worker_id: str,
        *,
        progress: float,
        stage: str,
        processed: int | None = None,
        total: int | None = None,
    ) -> None:
        changed = self.session.execute(
            text(
                """update hcg.jobs
                   set progress = :progress, stage = :stage,
                       processed = :processed, total = :total
                   where id = cast(:job_id as uuid)
                     and status = 'running' and worker_id = :worker_id"""
            ),
            {
                "job_id": job_id,
                "worker_id": worker_id,
                "progress": progress,
                "stage": stage,
                "processed": processed,
                "total": total,
            },
        )
        if changed.rowcount:
            self._event(job_id, "running", stage, progress, processed, total)
        self.session.commit()

    def renew_lease(self, job_id: str, worker_id: str) -> bool:
        changed = self.session.execute(
            text(
                """update hcg.jobs
                   set lease_expires_at = now() + interval '90 seconds'
                   where id = cast(:job_id as uuid)
                     and status = 'running' and worker_id = :worker_id"""
            ),
            {"job_id": job_id, "worker_id": worker_id},
        )
        self.session.commit()
        return bool(changed.rowcount)

    def recover_expired(self) -> int:
        rows = (
            self.session.execute(
                text(
                    """select id, attempt, max_attempts from hcg.jobs
                   where status = 'running' and lease_expires_at < now()
                   for update skip locked"""
                )
            )
            .mappings()
            .all()
        )
        for row in rows:
            status = "retrying" if row["attempt"] < row["max_attempts"] else "dead_letter"
            self.session.execute(
                text(
                    """update hcg.jobs
                       set status = :status, stage = :status, worker_id = null,
                           lease_expires_at = null, available_at = now(),
                           last_error_code = 'lease_expired',
                           last_error_message = 'Worker lease expired before completion'
                       where id = :job_id"""
                ),
                {"status": status, "job_id": row["id"]},
            )
            self._event(str(row["id"]), status, status, 0)
        self.session.commit()
        return len(rows)

    def complete(self, job_id: str, worker_id: str, result: dict) -> None:
        changed = self.session.execute(
            text(
                """update hcg.jobs
                   set status = 'completed', progress = 1, stage = 'completed',
                       result = cast(:result as jsonb), completed_at = now(),
                       lease_expires_at = null
                   where id = cast(:job_id as uuid)
                     and status = 'running' and worker_id = :worker_id"""
            ),
            {"job_id": job_id, "worker_id": worker_id, "result": json.dumps(result)},
        )
        if changed.rowcount:
            self._event(job_id, "completed", "completed", 1)
        self.session.commit()

    def fail(
        self, job_id: str, worker_id: str, code: str, message: str, *, retryable: bool = False
    ) -> str:
        row = (
            self.session.execute(
                text(
                    """select attempt, max_attempts from hcg.jobs
                   where id = cast(:job_id as uuid) and status = 'running'
                     and worker_id = :worker_id for update"""
                ),
                {"job_id": job_id, "worker_id": worker_id},
            )
            .mappings()
            .first()
        )
        if row is None:
            self.session.rollback()
            return "lost_lease"
        status = (
            "retrying"
            if retryable and row["attempt"] < row["max_attempts"]
            else "dead_letter"
            if retryable
            else "failed"
        )
        delay = min(300, 2 ** min(row["attempt"], 8)) * random.uniform(0.8, 1.2)
        available_at = datetime.now(UTC) + timedelta(seconds=delay)
        changed = self.session.execute(
            text(
                """update hcg.jobs
                   set status = :status, stage = :status, failed_at = now(),
                       last_error_code = :code, last_error_message = :message,
                       worker_id = null, lease_expires_at = null,
                       available_at = :available_at
                   where id = cast(:job_id as uuid)
                     and status = 'running' and worker_id = :worker_id"""
            ),
            {
                "job_id": job_id,
                "worker_id": worker_id,
                "code": code,
                "message": message[:500],
                "status": status,
                "available_at": available_at,
            },
        )
        if changed.rowcount:
            self._event(job_id, status, status, 0)
        self.session.commit()
        return status

    def cancel_queued(self, job_id: str) -> bool:
        result = self.session.execute(
            text(
                """update hcg.jobs
                   set status = 'cancelled', stage = 'cancelled', completed_at = now()
                   where id = cast(:job_id as uuid)
                     and status in ('queued', 'retrying')"""
            ),
            {"job_id": job_id},
        )
        if result.rowcount:
            self._event(job_id, "cancelled", "cancelled", 0)
        self.session.commit()
        return result.rowcount > 0

    def manual_retry(self, job_id: str) -> bool:
        changed = self.session.execute(
            text(
                """update hcg.jobs
                   set status = 'queued', stage = 'queued', available_at = now(),
                       max_attempts = attempt + 3, worker_id = null,
                       lease_expires_at = null
                   where id = cast(:job_id as uuid)
                     and status in ('failed', 'dead_letter')"""
            ),
            {"job_id": job_id},
        )
        if changed.rowcount:
            self._event(job_id, "queued", "manual_retry", 0)
        self.session.commit()
        return bool(changed.rowcount)


class IdempotencyConflictError(ValueError):
    pass


def parse_job_id(value: str) -> str:
    """Reject malformed IDs before they reach a SQL UUID cast."""
    return str(UUID(value))
