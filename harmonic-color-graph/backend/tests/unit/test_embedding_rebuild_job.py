import json

import pytest

from app.core.config import AppSettings
from app.jobs.handlers import run_job
from pipeline.embedding_rebuild import prepare_embedding_rebuild
from pipeline.manifest import sha256_file
from tests.unit.test_pipeline_embeddings import _write_fixture


def test_embedding_job_publishes_complete_bundle_without_replacing_source(tmp_path):
    version = "cv-2026-09-test"
    source = tmp_path / version
    source.mkdir()
    _write_fixture(source)
    sentinel = source / "embeddings.parquet"
    sentinel.write_bytes(b"existing corpus output")
    before = {path.name: sha256_file(path) for path in source.iterdir()}
    events = []
    report = run_job(
        "embedding_rebuild",
        {"corpus_version": version},
        AppSettings(HCG_ARTIFACT_ROOT=str(tmp_path)),
        lambda *args: events.append(args),
    )
    output = tmp_path / report["artifact_bundle"]
    assert output.is_dir()
    assert report["activation_required"] is True
    assert report["summary"]["rows_written"] > 0
    assert json.loads((output / "rebuild.json").read_text()) == report
    assert set(path.name for path in output.iterdir()) == {
        "embeddings.parquet",
        "embedding_projection.parquet",
        "embedding-map.json",
        "rebuild.json",
    }
    assert {path.name: sha256_file(path) for path in source.iterdir()} == before
    assert all(
        sha256_file(output / name) == digest for name, digest in report["output_sha256"].items()
    )
    assert events[-1][1] == "embedding_artifacts_ready"
    assert not list((tmp_path / "embedding-rebuilds").glob(".building-*"))


def test_failed_embedding_build_does_not_publish_partial_outputs(tmp_path, monkeypatch):
    source = tmp_path / "cv-2026-09-test"
    source.mkdir()
    _write_fixture(source)

    def fail(sections, output):
        (output / "embeddings.parquet").write_bytes(b"partial")
        raise ValueError("training failed")

    monkeypatch.setattr("pipeline.stages.embeddings.run_embeddings", fail)
    with pytest.raises(ValueError, match="training failed"):
        prepare_embedding_rebuild(tmp_path, source.name, lambda *args: None)
    assert not list((tmp_path / "embedding-rebuilds").iterdir())
    assert not (source / "embeddings.parquet").exists()


def test_embedding_build_rejects_paths_and_missing_inputs(tmp_path):
    with pytest.raises(FileNotFoundError):
        prepare_embedding_rebuild(tmp_path, "../escape", lambda *args: None)
    (tmp_path / "cv-2026-09-test").mkdir()
    with pytest.raises(FileNotFoundError, match="sections.parquet"):
        prepare_embedding_rebuild(tmp_path, "cv-2026-09-test", lambda *args: None)


def test_api_accepts_embedding_job_instead_of_obsolete_f50_error(monkeypatch):
    from app.api.jobs_v2 import create_job
    from app.jobs.schemas import EmbeddingRebuildRequest

    queued = []

    class Repository:
        def __init__(self, session):
            pass

        def create(self, kind, payload, key):
            assert kind == "embedding_rebuild"
            return {"id": "job-test", "status": "queued"}, True

    class Queue:
        def enqueue(self, job_id):
            queued.append(job_id)

        def close(self):
            pass

    monkeypatch.setattr("app.api.jobs_v2.JobRepository", Repository)
    monkeypatch.setattr("app.api.jobs_v2.JobQueue.from_url", lambda _: Queue())
    request = EmbeddingRebuildRequest(
        type="embedding_rebuild", payload={"corpus_version": "cv-2026-09-test"}
    )
    result = create_job(request, object(), AppSettings(REDIS_URL="redis://unused"), None)
    assert result["data"]["status"] == "queued"
    assert queued == ["job-test"]
