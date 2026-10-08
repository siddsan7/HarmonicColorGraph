"""F31: end-to-end `run_evaluation`/`render_markdown` over tiny synthetic
train/eval artifacts (built through the real `ingest`/`analyze`/`ngrams`
pipeline stages, not hand-written parquet) -- no dependency on the real
264MB corpus.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

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
    eval_rows = (
        [_ingest_row(100 + i, f"test-{i}", progression, "test") for i in range(10)]
        + [_ingest_row(200 + i, f"train-eval-dup-{i}", progression, "train") for i in range(5)]
        + [_ingest_row(300 + i, f"dev-{i}", progression, "dev") for i in range(10)]
    )

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


def test_run_evaluation_produces_every_baseline_and_a_consistent_check(
    artifacts, tmp_path, monkeypatch
):
    train_version, eval_version = artifacts
    monkeypatch.setattr(prediction_module, "REPO_ROOT", tmp_path / "unrelated")
    report = run_evaluation(
        train_version=train_version,
        eval_version=eval_version,
        eval_split="test",
        sample_size=50,
        seed=1,
        artifact_root=tmp_path / "data" / "artifacts",
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


def test_dev_tuning_is_deterministic_and_uses_explicit_artifact_root(
    artifacts, tmp_path, monkeypatch
):
    train_version, eval_version = artifacts
    artifact_root = tmp_path / "data" / "artifacts"
    monkeypatch.setattr(prediction_module, "REPO_ROOT", tmp_path / "unrelated")
    report = prediction_module.tune_mixing_k(
        train_version=train_version,
        eval_version=eval_version,
        sample_size=20,
        seed=7,
        mixing_k_values=(10.0, 100.0),
        artifact_root=artifact_root,
    )
    assert report == prediction_module.tune_mixing_k(
        train_version=train_version,
        eval_version=eval_version,
        sample_size=20,
        seed=7,
        mixing_k_values=(10.0, 100.0),
        artifact_root=artifact_root,
    )
    assert report["versions"]["eval_split"] == "dev"
    assert report["leak_check"]["dev_song_count"] == 10
    assert report["sample"]["actual_size"] == 20
    assert report["selected_mixing_k"] in (10.0, 100.0)
    assert "Held-out test evidence" in prediction_module.render_tuning_markdown(report)
    monkeypatch.setenv("HCG_EVAL_ARTIFACT_ROOT", str(artifact_root))
    assert report == prediction_module.tune_mixing_k(
        train_version=train_version,
        eval_version=eval_version,
        sample_size=20,
        seed=7,
        mixing_k_values=(10.0, 100.0),
    )


def test_dev_tuning_rejects_train_test_overlap_before_scoring(artifacts, tmp_path, monkeypatch):
    train_version, eval_version = artifacts
    root = tmp_path / "data" / "artifacts"
    sections_path = root / eval_version / "sections.parquet"
    sections = pl.read_parquet(sections_path).with_columns(
        pl.when(pl.col("split") == "test")
        .then(pl.lit("train-0"))
        .otherwise(pl.col("song_id"))
        .alias("song_id")
    )
    sections.write_parquet(sections_path)

    def unexpected_scoring(*args, **kwargs):
        raise AssertionError("scoring started before leak check")

    monkeypatch.setattr(prediction_module, "sample_test_positions", unexpected_scoring)
    with pytest.raises(AssertionError, match="Leak detected.*test-split"):
        prediction_module.tune_mixing_k(
            train_version=train_version,
            eval_version=eval_version,
            sample_size=10,
            mixing_k_values=(100.0,),
            artifact_root=root,
        )


def test_dev_tuning_ignores_train_rows_in_eval_artifact(artifacts, tmp_path):
    train_version, eval_version = artifacts
    root = tmp_path / "data" / "artifacts"
    sections_path = root / eval_version / "sections.parquet"
    sections = pl.read_parquet(sections_path).with_columns(
        pl.when(pl.col("split") == "train")
        .then(pl.lit("train-0"))
        .otherwise(pl.col("song_id"))
        .alias("song_id")
    )
    sections.write_parquet(sections_path)
    tuning = prediction_module.tune_mixing_k(
        train_version=train_version,
        eval_version=eval_version,
        sample_size=10,
        mixing_k_values=(100.0,),
        artifact_root=root,
    )
    assert tuning["leak_check"]["checked_splits"] == ["dev", "test"]
    assert tuning["leak_check"]["dev_song_count"] == 10
    assert tuning["leak_check"]["test_song_count"] == 10


def test_tuning_selects_maximal_mrr_and_lower_k_on_ties(artifacts, tmp_path, monkeypatch):
    train_version, eval_version = artifacts

    class OraclePredictor:
        def __init__(self, store, max_order_cap, mixing_k=100.0):
            self.mixing_k = mixing_k

        def distribution(self, history, genre, section):
            if genre is None or self.mixing_k in (10.0, 20.0):
                return {"M:V": 0.9, "M:IV": 0.1}
            return {"M:IV": 0.9, "M:V": 0.1}

    position = SimpleNamespace(history=("M:I",), genre="pop", section="verse", actual="M:V")
    monkeypatch.setattr(prediction_module, "KNPredictor", OraclePredictor)
    monkeypatch.setattr(
        prediction_module, "sample_test_positions", lambda *args, **kwargs: [position]
    )
    report = prediction_module.tune_mixing_k(
        train_version=train_version,
        eval_version=eval_version,
        sample_size=1,
        mixing_k_values=(30.0, 20.0, 10.0),
        artifact_root=tmp_path / "data" / "artifacts",
    )
    assert report["candidates"] == [
        {"mixing_k": 30.0, "context_mrr": 0.5},
        {"mixing_k": 20.0, "context_mrr": 1.0},
        {"mixing_k": 10.0, "context_mrr": 1.0},
    ]
    assert report["selected_mixing_k"] == 10.0
    assert report["selected_context_mrr"] == 1.0


def test_tuning_rejects_invalid_grid_before_loading_artifacts():
    with pytest.raises(ValueError, match="finite positive"):
        prediction_module.tune_mixing_k(
            train_version="missing", eval_version="missing", mixing_k_values=(float("nan"),)
        )
    with pytest.raises(ValueError, match="unique"):
        prediction_module.tune_mixing_k(
            train_version="missing", eval_version="missing", mixing_k_values=(10.0, 10.0)
        )


def test_tuning_cli_writes_report_outside_tracked_docs(artifacts, tmp_path):
    train_version, eval_version = artifacts
    output_dir = tmp_path / "reports"
    prediction_module.main(
        [
            "tune-mixing-k",
            "--train-version",
            train_version,
            "--eval-version",
            eval_version,
            "--artifact-root",
            str(tmp_path / "data" / "artifacts"),
            "--sample-size",
            "10",
            "--mixing-k",
            "100",
            "--output-dir",
            str(output_dir),
        ]
    )
    assert (output_dir / "prediction-k-tuning.json").is_file()
    assert (output_dir / "prediction-k-tuning.md").is_file()
