"""Job handlers call existing pipeline services, never HTTP routes."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path

from pydantic import TypeAdapter

from app.core.config import AppSettings
from app.jobs.schemas import (
    EmbeddingRebuildRequest,
    EvaluationRunRequest,
    GraphRebuildRequest,
    JobRequest,
)

Progress = Callable[[float, str, int | None, int | None], None]


class JobTypeUnavailableError(RuntimeError):
    pass


def _graph_rebuild(request: GraphRebuildRequest, settings: AppSettings, progress: Progress) -> dict:
    from pipeline.load import load_corpus

    root = Path(settings.hcg_artifact_root).resolve()
    artifact_dir = (root / request.payload.corpus_version).resolve()
    if artifact_dir.parent != root or not artifact_dir.is_dir():
        raise FileNotFoundError("Corpus artifacts are not available for this version")

    db_url = settings.database_url_load or settings.database_url
    if not db_url.startswith("postgresql+psycopg://"):
        raise ValueError("Graph rebuild requires a PostgreSQL psycopg URL")
    progress(0.05, "loading_corpus", 0, 1)
    report = load_corpus(artifact_dir, db_url.replace("postgresql+psycopg://", "postgresql://", 1))
    progress(0.95, "loaded_corpus", 1, 1)
    return asdict(report)


def _evaluation_run(
    request: EvaluationRunRequest, settings: AppSettings, progress: Progress
) -> dict:
    source = Path(settings.hcg_evaluation_source).resolve()
    if not source.is_file():
        raise FileNotFoundError("Configured evaluation corpus is not available")
    progress(0.05, "evaluating", 0, request.payload.song_limit)
    if request.payload.suite == "keys":
        from pipeline.stages.evaluate_keys_corpus import evaluate
    else:
        from pipeline.stages.evaluate_labels_corpus import evaluate

    report = evaluate(source, request.payload.song_limit)
    progress(0.95, "report_ready", request.payload.song_limit, request.payload.song_limit)
    return {"suite": request.payload.suite, "report": report}


def run_job(kind: str, payload: dict, settings: AppSettings, progress: Progress) -> dict:
    request = TypeAdapter(JobRequest).validate_python({"type": kind, "payload": payload})
    if isinstance(request, GraphRebuildRequest):
        return _graph_rebuild(request, settings, progress)
    if isinstance(request, EvaluationRunRequest):
        return _evaluation_run(request, settings, progress)
    if isinstance(request, EmbeddingRebuildRequest):
        raise JobTypeUnavailableError("Embedding rebuild becomes available in F50")
    raise AssertionError("Unexpected allowlisted job request")
