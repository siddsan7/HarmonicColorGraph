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
from pipeline.stages._unimplemented import StageNotImplementedError  # noqa: E402
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


def test_unimplemented_downstream_stage_raises_clear_error(tmp_path, mini_corpus, monkeypatch):
    monkeypatch.setattr(cli, "REPO_ROOT", tmp_path)
    args = _make_args(tmp_path, mini_corpus, "cv-test-a", to_stage="embeddings")

    with pytest.raises(StageNotImplementedError, match="F50"):
        cli._run_build(args)


def test_from_stage_after_to_stage_is_rejected(tmp_path, mini_corpus, monkeypatch):
    monkeypatch.setattr(cli, "REPO_ROOT", tmp_path)
    args = _make_args(tmp_path, mini_corpus, "cv-test-a", from_stage="analyze", to_stage="ingest")

    with pytest.raises(SystemExit):
        cli._run_build(args)
