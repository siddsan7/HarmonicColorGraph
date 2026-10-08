"""F20 `hcg-build run`: end-to-end orchestration over the synthetic mini
corpus -- stage sequencing, manifest, and the `--from-stage`/`--to-stage`
window on the still-unimplemented downstream stages.
"""

import argparse
import json
from pathlib import Path

import pytest

pl = pytest.importorskip("polars")

import pipeline.cli as cli  # noqa: E402
from pipeline.synth import write_mini_corpus  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[3]


def _make_args(tmp_path: Path, source: Path, version: str, **overrides) -> argparse.Namespace:
    defaults = {
        "source": source,
        "version": version,
        "workers": 1,
        "limit": 15,
        "split": "all",
        "from_stage": None,
        "to_stage": "analyze",
    }
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


@pytest.fixture
def mini_corpus(tmp_path: Path) -> Path:
    return write_mini_corpus(tmp_path / "mini_corpus.csv", song_count=30, seed=1)


def test_run_writes_manifest_and_artifacts(tmp_path, mini_corpus, monkeypatch):
    monkeypatch.setattr(cli, "REPO_ROOT", tmp_path)
    args = _make_args(tmp_path, mini_corpus, "cv-test-a")

    cli._run_build(args)

    artifact_dir = tmp_path / "data" / "artifacts" / "cv-test-a"
    manifest = json.loads((artifact_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["version"] == "cv-test-a"
    assert manifest["license"] == "CC BY-NC 4.0"
    assert set(manifest["output_hashes"]) == {"ingest.parquet", "sections.parquet"}
    assert set(manifest["stage_timings_s"]) == {"ingest", "analyze"}
    assert manifest["row_counts"]["songs_ingested"] == 15
    assert manifest["params"]["build_status"] == "complete"
    assert (artifact_dir / "ingest.parquet").exists()
    assert (artifact_dir / "sections.parquet").exists()


def test_run_twice_yields_identical_manifest_hashes(tmp_path, mini_corpus, monkeypatch):
    monkeypatch.setattr(cli, "REPO_ROOT", tmp_path)
    cli._run_build(_make_args(tmp_path, mini_corpus, "cv-test-a"))
    first = json.loads(
        (tmp_path / "data" / "artifacts" / "cv-test-a" / "manifest.json").read_text()
    )["output_hashes"]

    monkeypatch.setattr(cli, "REPO_ROOT", tmp_path.parent / (tmp_path.name + "-2"))
    cli.REPO_ROOT.mkdir()
    cli._run_build(_make_args(cli.REPO_ROOT, mini_corpus, "cv-test-a"))
    second = json.loads(
        (cli.REPO_ROOT / "data" / "artifacts" / "cv-test-a" / "manifest.json").read_text()
    )["output_hashes"]

    assert first == second


def test_snapshot_stage_exports_bounded_global_graph(tmp_path, mini_corpus, monkeypatch):
    # STAGE_ORDER runs the real
    # `embeddings` stage (F50, gensim-backed) on the way there; the
    # `backend (unit)` CI job installs `.[dev,pipeline]` only, not the
    # optional `[ml]` extra, so this needs the same importorskip every other
    # ml-dependent pipeline test uses.
    pytest.importorskip("gensim")
    monkeypatch.setattr(cli, "REPO_ROOT", tmp_path)
    args = _make_args(tmp_path, mini_corpus, "cv-test-a", to_stage="snapshot")

    cli._run_build(args)
    snapshot = tmp_path / "public" / "snapshot" / "graph-core.json"
    payload = json.loads(snapshot.read_text(encoding="utf-8"))
    assert snapshot.stat().st_size <= 500_000
    assert payload["context"] == "global"
    assert any(node["id"] == "function:M:I" for node in payload["nodes"])
    assert all(node["label"] == node["id"].removeprefix("function:") for node in payload["nodes"])
    assert all(edge["type"] == "TRANSITIONS_TO" for edge in payload["edges"])
    manifest_path = tmp_path / "data/artifacts/cv-test-a/manifest.json"
    before = json.loads(manifest_path.read_text(encoding="utf-8"))
    cli._run_build(
        _make_args(tmp_path, mini_corpus, "cv-test-a", from_stage="snapshot", to_stage="snapshot")
    )
    after = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert after["params"]["embedding_default_model"] == before["params"]["embedding_default_model"]
    assert (
        after["output_hashes"]["embeddings.parquet"]
        == before["output_hashes"]["embeddings.parquet"]
    )


def test_from_stage_after_to_stage_is_rejected(tmp_path, mini_corpus, monkeypatch):
    monkeypatch.setattr(cli, "REPO_ROOT", tmp_path)
    args = _make_args(tmp_path, mini_corpus, "cv-test-a", from_stage="analyze", to_stage="ingest")

    with pytest.raises(SystemExit):
        cli._run_build(args)


def test_upstream_rerun_invalidates_downstream_completion(tmp_path, mini_corpus, monkeypatch):
    from pipeline.load import _validate_artifacts
    from pipeline.manifest import Manifest

    monkeypatch.setattr(cli, "REPO_ROOT", tmp_path)
    cli._run_build(_make_args(tmp_path, mini_corpus, "cv-test-a"))
    path = tmp_path / "data/artifacts/cv-test-a/manifest.json"
    manifest = json.loads(path.read_text())
    manifest["params"]["embedding_default_model"] = "test-model"
    manifest["output_hashes"]["embeddings.parquet"] = "stale-generation"
    manifest["row_counts"]["embeddings_rows"] = 100
    manifest["stage_timings_s"]["embeddings"] = 10
    manifest["budget_estimate_mb"]["color_profiles"] = 2
    path.write_text(json.dumps(manifest))
    cli._run_build(_make_args(tmp_path, mini_corpus, "cv-test-a", from_stage="analyze"))
    rebuilt = Manifest.read(path)
    assert "embedding_default_model" not in rebuilt.params
    assert "embeddings.parquet" not in rebuilt.output_hashes
    assert "embeddings_rows" not in rebuilt.row_counts
    assert "embeddings" not in rebuilt.stage_timings_s
    assert "color_profiles" not in rebuilt.budget_estimate_mb
    with pytest.raises(ValueError, match="Missing completed pipeline artifact"):
        _validate_artifacts(path.parent, rebuilt)


@pytest.mark.parametrize("changed", [False, True])
def test_resume_rejects_missing_or_changed_prerequisites(
    tmp_path, mini_corpus, monkeypatch, changed
):
    monkeypatch.setattr(cli, "REPO_ROOT", tmp_path)
    cli._run_build(_make_args(tmp_path, mini_corpus, "cv-test-a"))
    artifact_dir = tmp_path / "data/artifacts/cv-test-a"
    path = artifact_dir / "manifest.json"
    before = path.read_bytes()
    if changed:
        sections = artifact_dir / "sections.parquet"
        pl.read_parquet(sections).head(1).write_parquet(sections)
    with pytest.raises(ValueError, match="prerequisite"):
        cli._run_build(
            _make_args(tmp_path, mini_corpus, "cv-test-a", from_stage="ngrams", to_stage="ngrams")
        )
    assert path.read_bytes() == before


def test_failed_stage_preserves_completed_hashes_and_blocks_loading(
    tmp_path, mini_corpus, monkeypatch
):
    from pipeline.load import _validate_artifacts
    from pipeline.manifest import Manifest

    monkeypatch.setattr(cli, "REPO_ROOT", tmp_path)

    def fail_aggregate(*_args):
        raise RuntimeError("injected aggregate failure")

    monkeypatch.setattr("pipeline.stages.aggregate.run_aggregate", fail_aggregate)
    with pytest.raises(RuntimeError, match="injected aggregate failure"):
        cli._run_build(_make_args(tmp_path, mini_corpus, "cv-test-a", to_stage="aggregate"))
    artifact_dir = tmp_path / "data/artifacts/cv-test-a"
    manifest = Manifest.read(artifact_dir / "manifest.json")
    assert manifest.params["build_status"] == "running"
    assert set(manifest.output_hashes) == {"ingest.parquet", "sections.parquet"}
    assert set(manifest.stage_timings_s) == {"ingest", "analyze"}
    with pytest.raises(ValueError, match="build has not completed"):
        _validate_artifacts(artifact_dir, manifest)

    cli._run_build(
        _make_args(tmp_path, mini_corpus, "cv-test-a", from_stage="analyze", to_stage="analyze")
    )
    assert Manifest.read(artifact_dir / "manifest.json").params["build_status"] == "complete"
