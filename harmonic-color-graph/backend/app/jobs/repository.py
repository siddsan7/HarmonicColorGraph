"""Postgres job ledger. Redis messages never carry payloads or durable state."""

from __future__ import annotations

import json
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session


class JobRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, kind: str, payload: dict) -> dict:
        row = (
            self.session.execute(
                text(
                    """insert into hcg.jobs (type, payload)
                   values (:kind, cast(:payload as jsonb))
                   returning id"""
                ),
                {"kind": kind, "payload": json.dumps(payload)},
            )
            .mappings()
            .one()
        )
        self._event(str(row["id"]), "queued", "queued", 0)
        self.session.commit()
        return self.get(str(row["id"]))  # type: ignore[return-value]

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
                          last_error_code, last_error_message, worker_id
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
                """select id from hcg.jobs where status = 'queued'
                   order by created_at limit :limit"""
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
                       stage = 'starting'
                   where id = cast(:job_id as uuid) and status = 'queued'
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

    def complete(self, job_id: str, worker_id: str, result: dict) -> None:
        changed = self.session.execute(
            text(
                """update hcg.jobs
                   set status = 'completed', progress = 1, stage = 'completed',
                       result = cast(:result as jsonb), completed_at = now()
                   where id = cast(:job_id as uuid)
                     and status = 'running' and worker_id = :worker_id"""
            ),
            {"job_id": job_id, "worker_id": worker_id, "result": json.dumps(result)},
        )
        if changed.rowcount:
            self._event(job_id, "completed", "completed", 1)
        self.session.commit()

    def fail(self, job_id: str, worker_id: str, code: str, message: str) -> None:
        changed = self.session.execute(
            text(
                """update hcg.jobs
                   set status = 'failed', stage = 'failed', failed_at = now(),
                       last_error_code = :code, last_error_message = :message
                   where id = cast(:job_id as uuid)
                     and status = 'running' and worker_id = :worker_id"""
            ),
            {"job_id": job_id, "worker_id": worker_id, "code": code, "message": message[:500]},
        )
        if changed.rowcount:
            self._event(job_id, "failed", "failed", 0)
        self.session.commit()

    def cancel_queued(self, job_id: str) -> bool:
        result = self.session.execute(
            text(
                """update hcg.jobs
                   set status = 'cancelled', stage = 'cancelled', completed_at = now()
                   where id = cast(:job_id as uuid) and status = 'queued'"""
            ),
            {"job_id": job_id},
        )
        if result.rowcount:
            self._event(job_id, "cancelled", "cancelled", 0)
        self.session.commit()
        return result.rowcount > 0


def parse_job_id(value: str) -> str:
    """Reject malformed IDs before they reach a SQL UUID cast."""
    return str(UUID(value))
