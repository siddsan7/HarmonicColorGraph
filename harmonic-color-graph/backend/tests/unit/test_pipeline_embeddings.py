"""F50 embeddings pipeline stage: Chord2Vec (gensim Word2Vec), FastRP over the
global function graph, SIF-weighted pattern vectors, and UMAP/SVD projections.

Small, seeded, synthetic fixtures (not the real corpus) -- the stage itself
is trained purely from `sections.parquet`/`transitions.parquet`/
`patterns.parquet`, so a small repeated-sentence corpus is enough to make
every code path (chord2vec, fastrp, pattern vectors, projections) run for
real, just not enough for the triplet suite's Checks bar (see
`docs/eval/embeddings.md`, generated separately against a real corpus
sample via `pipeline.cli embedding-report`).
"""

from pathlib import Path

import pytest

pl = pytest.importorskip("polars")
pytest.importorskip("gensim")

from pipeline.embedding_eval import TRIPLETS, evaluate_embeddings, render_report  # noqa: E402
from pipeline.stages.embeddings import run_embeddings  # noqa: E402

SECTIONS_SCHEMA = {
    "song_index": pl.Int64,
    "song_id": pl.Utf8,
    "ordinal": pl.Int64,
    "section": pl.Utf8,
    "local_key": pl.Utf8,
    "key_conf": pl.Float64,
    "ambiguous": pl.Boolean,
    "tokens": pl.List(pl.Utf8),
    "figures": pl.List(pl.Utf8),
    "chords": pl.List(pl.Utf8),
    "labels": pl.List(pl.Utf8),
    "genre": pl.Utf8,
    "decade": pl.Utf8,
    "spotify_id": pl.Utf8,
    "split": pl.Utf8,
    "repeat_count": pl.Int64,
}

# A handful of common-progression "sentences", repeated with light variation
# so gensim's default min_count (relaxed to 1 for this fixture's scale) sees
# every token enough times to place it in the vocabulary, and FastRP's graph
# has real repeated edges to walk.
_LOOPS = [
    ["M:I", "M:V", "M:vi", "M:IV"],
    ["M:I", "M:IV", "M:V", "M:I"],
    ["M:ii", "M:V", "M:I", "M:vi"],
    ["M:I", "M:vi", "M:IV", "M:V"],
    ["M:V7", "M:I", "M:IV", "M:V7"],
    ["M:vi", "M:IV", "M:I", "M:V"],
]


def _section_row(index: int, tokens: list[str]) -> dict:
    return {
        "song_index": index,
        "song_id": str(index),
        "ordinal": 0,
        "section": "verse",
        "local_key": "C major",
        "key_conf": 0.9,
        "ambiguous": False,
        "tokens": tokens,
        "figures": tokens,
        "chords": ["C:maj"] * len(tokens),
        "labels": [],
        "genre": "pop",
        "decade": "2020s",
        "spotify_id": None,
        "split": "train",
        "repeat_count": 1,
    }


def _write_fixture(tmp_path: Path) -> Path:
    rows = [_section_row(i, loop) for i, loop in enumerate(_LOOPS * 10)]
    pl.DataFrame(rows, schema=SECTIONS_SCHEMA).write_parquet(tmp_path / "sections.parquet")

    transitions_rows = []
    for loop in _LOOPS:
        for a, b in zip(loop, loop[1:] + loop[:1], strict=True):
            transitions_rows.append(
                {
                    "context": "global",
                    "from_token": a,
                    "to_token": b,
                    "count": 10,
                    "prob": 0.5,
                    "pmi": 0.1,
                    "support": 10,
                }
            )
    pl.DataFrame(
        transitions_rows,
        schema={
            "context": pl.Utf8,
            "from_token": pl.Utf8,
            "to_token": pl.Utf8,
            "count": pl.Int64,
            "prob": pl.Float64,
            "pmi": pl.Float64,
            "support": pl.Int64,
        },
    ).write_parquet(tmp_path / "transitions.parquet")

    patterns_rows = [
        {"pattern": " ".join(loop), "length": len(loop), "support": 10} for loop in _LOOPS
    ]
    pl.DataFrame(
        patterns_rows, schema={"pattern": pl.Utf8, "length": pl.Int64, "support": pl.Int64}
    ).write_parquet(tmp_path / "patterns.parquet")
    return tmp_path


def test_run_embeddings_writes_function_and_pattern_vectors(tmp_path: Path):
    _write_fixture(tmp_path)
    summary = run_embeddings(tmp_path / "sections.parquet", tmp_path, min_count=1)

    assert summary.train_sections == len(_LOOPS) * 10
    assert summary.model_vocab > 0
    assert summary.function_rows > 0
    assert summary.pattern_rows == len(_LOOPS)

    frame = pl.read_parquet(tmp_path / "embeddings.parquet")
    assert set(frame["subject_type"].unique().to_list()) == {"function", "pattern"}
    assert set(frame["model"].unique().to_list()) >= {"chord2vec", "fastrp"}
    for vec in frame["vec"]:
        assert len(vec) == 64
        norm = sum(value * value for value in vec) ** 0.5
        assert norm == pytest.approx(1.0, abs=1e-3)


def test_run_embeddings_writes_a_2d_projection_for_every_function(tmp_path: Path):
    _write_fixture(tmp_path)
    run_embeddings(tmp_path / "sections.parquet", tmp_path, min_count=1)
    projection = pl.read_parquet(tmp_path / "embedding_projection.parquet")
    functions = projection.filter(pl.col("subject_type") == "function")
    embeddings = pl.read_parquet(tmp_path / "embeddings.parquet")
    expected = embeddings.filter(pl.col("subject_type") == "function").height
    assert functions.height == expected
    assert set(functions.columns) == {"subject_type", "subject_id", "model", "x", "y"}


def test_run_embeddings_requires_train_split_sections(tmp_path: Path):
    rows = [_section_row(0, _LOOPS[0])]
    rows[0]["split"] = "test"
    pl.DataFrame(rows, schema=SECTIONS_SCHEMA).write_parquet(tmp_path / "sections.parquet")
    pl.DataFrame(
        schema={
            "context": pl.Utf8,
            "from_token": pl.Utf8,
            "to_token": pl.Utf8,
            "count": pl.Int64,
            "prob": pl.Float64,
            "pmi": pl.Float64,
            "support": pl.Int64,
        }
    ).write_parquet(tmp_path / "transitions.parquet")
    pl.DataFrame(
        schema={"pattern": pl.Utf8, "length": pl.Int64, "support": pl.Int64}
    ).write_parquet(tmp_path / "patterns.parquet")
    with pytest.raises(ValueError, match="train-split"):
        run_embeddings(tmp_path / "sections.parquet", tmp_path, min_count=1)


def test_evaluate_embeddings_scores_every_triplet_against_a_full_vocabulary(tmp_path: Path):
    """A model whose vectors *are* the triplet tokens themselves (one-hot in
    disguise, deterministic) should evaluate every one of the 40 triplets --
    exercising the real scoring path end to end without depending on a real
    corpus's trained semantics."""
    import numpy as np

    tokens = sorted({token for triplet in TRIPLETS for token in triplet})
    rng = np.random.default_rng(0)
    base = {token: rng.normal(size=64).astype("float32") for token in tokens}
    # Nudge each triplet's positive pair closer than the negative pair so the
    # deterministic scoring assertion below is meaningful, not incidental.
    for anchor, positive, negative in TRIPLETS:
        base[positive] = base[anchor] + 0.05 * rng.normal(size=64).astype("float32")
        base[negative] = -base[anchor] + 0.05 * rng.normal(size=64).astype("float32")

    rows = [
        {"subject_type": "function", "subject_id": token, "model": model, "vec": vec.tolist()}
        for model in ("chord2vec", "fastrp")
        for token, vec in base.items()
    ]
    schema = {
        "subject_type": pl.Utf8,
        "subject_id": pl.Utf8,
        "model": pl.Utf8,
        "vec": pl.List(pl.Float32),
    }
    path = tmp_path / "embeddings.parquet"
    pl.DataFrame(rows, schema=schema).write_parquet(path)

    evaluations, default = evaluate_embeddings(path)
    assert {item.model for item in evaluations} == {"chord2vec", "fastrp"}
    for item in evaluations:
        assert item.evaluated == len(TRIPLETS)
        # Every token pair was nudged toward its intended ordering, so this
        # should clear chance (50%) comfortably; the plan's >= 80% bar is a
        # real-corpus-trained-model claim, checked separately by
        # `docs/eval/embeddings.md` against actual trained vectors, not by
        # this deterministic-but-noisy synthetic fixture.
        assert item.passed >= len(TRIPLETS) * 0.6
    assert default in {"chord2vec", "fastrp"}

    report = render_report(evaluations, default, "test-corpus")
    assert "# Embedding intrinsic evaluation" in report
    assert f"Default model: `{default}`." in report
    assert report.count("|") > 0
    for anchor, positive, negative in TRIPLETS[:3]:
        assert anchor in report and positive in report and negative in report


def test_evaluate_embeddings_handles_an_empty_model(tmp_path: Path):
    schema = {
        "subject_type": pl.Utf8,
        "subject_id": pl.Utf8,
        "model": pl.Utf8,
        "vec": pl.List(pl.Float32),
    }
    path = tmp_path / "embeddings.parquet"
    pl.DataFrame(schema=schema).write_parquet(path)
    evaluations, default = evaluate_embeddings(path)
    assert all(item.evaluated == 0 and item.score == 0.0 for item in evaluations)
    assert default in {"chord2vec", "fastrp"}
