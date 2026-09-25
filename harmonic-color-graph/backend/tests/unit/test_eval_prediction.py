"""F31: end-to-end `run_evaluation`/`render_markdown` over tiny synthetic
train/eval artifacts (built through the real `ingest`/`analyze`/`ngrams`
pipeline stages, not hand-written parquet) -- no dependency on the real
264MB corpus.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pl = pytest.importorskip("polars")

from pipeline.stages.analyze import run_analyze  # noqa: E402
from pipeline.stages.ingest import INGEST_SCHEMA  # noqa: E402
from pipeline.stages.ngrams import run_ngrams  # noqa: E402
from tests.eval import prediction as prediction_module  # noqa: E402
from tests.eval.baselines import V2_FULL_NAME  # noqa: E402
from tests.eval.prediction import assert_no_leakage, render_markdown, run_evaluation  # noqa: E402


def _ingest_row(song_index, song_id, chords, split, genre="pop"):
    return {
        "song_index": song_index,
        "song_id": song_id,
        "ordinal": 0,
        "section": "verse",
        "chords": chords,
        "genre": genre,
        "subgenre": None,
        "decade": "2020s",
        "spotify_id": None,
        "split": split,
        "repeat_count": 1,
    }


def _build_artifact(artifact_dir: Path, rows: list[dict]) -> None:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    ingest_path = artifact_dir / "ingest.parquet"
    sections_path = artifact_dir / "sections.parquet"
    pl.DataFrame(rows, schema=INGEST_SCHEMA).write_parquet(ingest_path)
    run_analyze(ingest_path, sections_path, workers=1)
    run_ngrams(sections_path, artifact_dir / "ngrams.parquet", min_context_observations=1)


@pytest.fixture
def artifacts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[str, str]:
    monkeypatch.setattr(prediction_module, "REPO_ROOT", tmp_path)
    (tmp_path / "data" / "artifacts").mkdir(parents=True)

    # A repeated I-IV-V-I progression, common enough to survive ngrams'
    # pruning thresholds even at this tiny scale.
    progression = "C F G C F G C F G C"
    train_rows = [_ingest_row(i, f"train-{i}", progression, "train") for i in range(30)]
    eval_rows = [_ingest_row(100 + i, f"test-{i}", progression, "test") for i in range(10)] + [
        _ingest_row(200 + i, f"train-eval-dup-{i}", progression, "train") for i in range(5)
    ]

    _build_artifact(tmp_path / "data" / "artifacts" / "train-a", train_rows)
    _build_artifact(tmp_path / "data" / "artifacts" / "eval-a", eval_rows)
    return "train-a", "eval-a"


def test_leak_check_passes_when_splits_are_disjoint(artifacts):
    train_version, eval_version = artifacts
    report = assert_no_leakage(train_version, eval_version, "test")
    assert report["passed"]
    assert report["overlap"] == 0
    assert report["test_song_count"] == 10


def test_leak_check_raises_when_a_test_song_is_also_in_train(tmp_path, monkeypatch):
    monkeypatch.setattr(prediction_module, "REPO_ROOT", tmp_path)
    (tmp_path / "data" / "artifacts").mkdir(parents=True)
    shared_song = "shared-song"
    progression = "C F G C"
    _build_artifact(
        tmp_path / "data" / "artifacts" / "train-b",
        [_ingest_row(0, shared_song, progression, "train")],
    )
    _build_artifact(
        tmp_path / "data" / "artifacts" / "eval-b",
        [_ingest_row(0, shared_song, progression, "test")],
    )
    with pytest.raises(AssertionError, match="Leak detected"):
        assert_no_leakage("train-b", "eval-b", "test")


def test_run_evaluation_produces_every_baseline_and_a_consistent_check(artifacts):
    train_version, eval_version = artifacts
    report = run_evaluation(
        train_version=train_version,
        eval_version=eval_version,
        eval_split="test",
        sample_size=50,
        seed=1,
    )
    assert report["leak_check"]["passed"]
    assert V2_FULL_NAME in report["overall"]
    assert "v1_hard_backoff_bigram" in report["overall"]
    assert report["sample"]["actual_size"] > 0

    check = report["check"]
    assert check["delta"] == pytest.approx(check["v2_full_mrr"] - check["v1_mrr"])
    assert check["passed"] == (check["v2_full_mrr"] >= check["v1_mrr"] + check["required_delta"])

    for dimension in ("genre", "section", "mode", "context_depth"):
        assert V2_FULL_NAME in report["slices"][dimension]


def test_render_markdown_includes_the_headline_check_and_metrics_table(artifacts):
    train_version, eval_version = artifacts
    report = run_evaluation(
        train_version=train_version, eval_version=eval_version, sample_size=50, seed=1
    )
    markdown = render_markdown(report)
    assert "## Headline check" in markdown
    assert V2_FULL_NAME in markdown
    assert "v1_hard_backoff_bigram" in markdown
    assert "## By genre" in markdown
