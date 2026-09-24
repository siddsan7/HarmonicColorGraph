"""F30: interpolated Kneser-Ney prediction with context backoff, checked
against hand-worked distributions and, via Hypothesis, over random
histories.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.predict.ngram import InMemoryNgramStore, KNPredictor


def _abc_store() -> InMemoryNgramStore:
    """Same corpus as `tests/unit/test_pipeline_ngrams.py`'s hand-worked
    example: the token sequence "A B C A B D"."""
    store = InMemoryNgramStore()
    store.add_row(
        "global",
        1,
        "",
        total=6,
        distinct_next=4,
        next={"A": 2, "B": 2, "C": 1, "D": 1},
        cont={"A": 1, "B": 1, "C": 1, "D": 1},
    )
    store.add_row("global", 2, "A", total=2, distinct_next=1, next={"B": 2}, cont={"B": 1})
    store.add_row(
        "global",
        2,
        "B",
        total=2,
        distinct_next=2,
        next={"C": 1, "D": 1},
        cont={"C": 1, "D": 1},
    )
    return store


def test_hand_worked_order2_backoff_matches_the_kn_formula_by_hand():
    # D = n1/(n1+2n2) pooled over BOTH order-2 histories: raw counts are
    # A->B=2, B->C=1, B->D=1, so n1=2 (the two 1s), n2=1 (the one 2) ->
    # D = 2/(2+2*1) = 0.5.
    predictor = KNPredictor(_abc_store())
    dist = predictor.distribution(["A"])

    # own(B) = max(2-0.5,0)/2 = 0.75; lambda = 0.5*1/2 = 0.25;
    # unigram cont dist is uniform 1/4 per token (cont totals 4) ->
    # B = 0.75 + 0.25*0.25 = 0.8125; everyone else = 0.25*0.25 = 0.0625.
    assert dist["B"] == pytest.approx(0.8125)
    assert dist["A"] == pytest.approx(0.0625)
    assert dist["C"] == pytest.approx(0.0625)
    assert dist["D"] == pytest.approx(0.0625)
    assert sum(dist.values()) == pytest.approx(1.0)


def test_different_histories_produce_different_top_predictions():
    predictor = KNPredictor(_abc_store())
    after_a = predictor.predict(["A"], top_n=1).predictions[0].token
    after_b = predictor.predict(["B"], top_n=1).predictions[0].token
    assert after_a == "B"
    assert after_b in ("C", "D")
    assert after_a != after_b


def test_unknown_history_falls_back_to_the_unigram_floor():
    predictor = KNPredictor(_abc_store())
    # "Z" was never observed as a history at order 2, so order 2 has no
    # row and the prediction falls straight through to the (order-1)
    # continuation-count unigram, uniform over the 4-token vocabulary.
    dist = predictor.distribution(["Z"])
    assert dist == pytest.approx({"A": 0.25, "B": 0.25, "C": 0.25, "D": 0.25})


def test_breakdown_sums_to_the_predicted_probability_and_backoff_path_is_specific_first():
    predictor = KNPredictor(_abc_store())
    result = predictor.predict(["A"], top_n=4)
    assert result.backoff_path == (("global", 2), ("global", 1))
    token_b = next(p for p in result.predictions if p.token == "B")
    assert sum(item.contribution for item in token_b.breakdown) == pytest.approx(
        token_b.probability
    )
    assert token_b.support == 2  # the raw A->B count from the order-2 row
    # Every breakdown entry names a step that was actually on the backoff
    # path, most-specific order first.
    assert [(item.context, item.order) for item in token_b.breakdown] == [
        ("global", 2),
        ("global", 1),
    ]


def test_context_backoff_mixes_genre_evidence_with_global_by_beta():
    store = InMemoryNgramStore()
    store.add_row(
        "global", 1, "", total=4, distinct_next=2, next={"A": 2, "B": 2}, cont={"A": 1, "B": 1}
    )
    store.add_row("global", 2, "A", total=2, distinct_next=1, next={"B": 2}, cont={"B": 1})
    store.add_row(
        "genre:pop",
        1,
        "",
        total=200,
        distinct_next=2,
        next={"A": 100, "C": 100},
        cont={"A": 1, "C": 1},
    )
    store.add_row("genre:pop", 2, "A", total=100, distinct_next=1, next={"C": 100}, cont={"C": 1})

    predictor = KNPredictor(store)
    without_genre = predictor.distribution(["A"])
    with_genre = predictor.distribution(["A"], genre="pop")

    assert without_genre.get("C", 0.0) == 0.0  # global has never seen A->C
    assert with_genre["C"] > 0.0  # the pop context brings it in
    # beta = n_ctx_h / (n_ctx_h + K) = 100 / (100 + 100) = 0.5 with both
    # rows' own terms fully saturating their order (D = 0 since the sole
    # raw count at each is neither 1 nor 2), so it's an even split.
    assert with_genre["B"] == pytest.approx(0.5)
    assert with_genre["C"] == pytest.approx(0.5)
    assert sum(with_genre.values()) == pytest.approx(1.0)


def test_genre_with_too_little_data_defers_almost_entirely_to_global():
    store = InMemoryNgramStore()
    store.add_row(
        "global",
        1,
        "",
        total=1000,
        distinct_next=2,
        next={"A": 500, "B": 500},
        cont={"A": 1, "B": 1},
    )
    store.add_row("global", 2, "A", total=500, distinct_next=1, next={"B": 500}, cont={"B": 1})
    # A brand-new genre with exactly one observation of "A" -> "C".
    store.add_row("genre:obscure", 1, "", total=1, distinct_next=1, next={"C": 1}, cont={"C": 1})
    store.add_row("genre:obscure", 2, "A", total=1, distinct_next=1, next={"C": 1}, cont={"C": 1})

    predictor = KNPredictor(store)
    dist = predictor.distribution(["A"], genre="obscure")
    # beta = 1/(1+100) ~= 0.0099, so global's answer still dominates.
    assert dist["B"] > 0.95


def test_no_active_corpus_raises_lookup_error():
    predictor = KNPredictor(InMemoryNgramStore())
    with pytest.raises(LookupError):
        predictor.predict(["A"])


@given(
    history=st.lists(st.sampled_from(["A", "B", "C", "D", "Z"]), min_size=0, max_size=4),
    genre=st.sampled_from([None, "pop", "obscure"]),
)
@settings(max_examples=1000)
def test_full_distribution_always_sums_to_one(history, genre):
    store = InMemoryNgramStore()
    store.add_row(
        "global",
        1,
        "",
        total=6,
        distinct_next=4,
        next={"A": 2, "B": 2, "C": 1, "D": 1},
        cont={"A": 1, "B": 1, "C": 1, "D": 1},
    )
    store.add_row("global", 2, "A", total=2, distinct_next=1, next={"B": 2}, cont={"B": 1})
    store.add_row(
        "global",
        2,
        "B",
        total=2,
        distinct_next=2,
        next={"C": 1, "D": 1},
        cont={"C": 1, "D": 1},
    )
    store.add_row(
        "genre:pop",
        1,
        "",
        total=10,
        distinct_next=3,
        next={"A": 4, "B": 3, "C": 3},
        cont={"A": 1, "B": 1, "C": 1},
    )
    store.add_row(
        "genre:pop", 2, "A", total=4, distinct_next=2, next={"B": 3, "C": 1}, cont={"B": 1, "C": 1}
    )

    predictor = KNPredictor(store)
    dist = predictor.distribution(history, genre=genre)
    assert sum(dist.values()) == pytest.approx(1.0, abs=1e-9)
    assert all(probability >= 0.0 for probability in dist.values())


def test_in_memory_store_builds_from_ngrams_pipeline_artifact_rows(tmp_path: Path):
    pl = pytest.importorskip("polars")
    from pipeline.stages.analyze import SECTIONS_SCHEMA
    from pipeline.stages.ngrams import run_ngrams

    def section_row(tokens):
        return {
            "song_index": 0,
            "song_id": "0",
            "ordinal": 0,
            "section": None,
            "local_key": "C major",
            "key_conf": 0.9,
            "ambiguous": False,
            "tokens": tokens,
            "figures": tokens,
            "chords": ["C:maj"] * len(tokens),
            "labels": [],
            "genre": None,
            "decade": None,
            "spotify_id": None,
            "split": "train",
            "repeat_count": 1,
        }

    sections_path = tmp_path / "sections.parquet"
    pl.DataFrame(
        [section_row(["A", "B", "C", "A", "B", "D"])], schema=SECTIONS_SCHEMA
    ).write_parquet(sections_path)
    output_path = tmp_path / "ngrams.parquet"
    run_ngrams(sections_path, output_path)

    store = InMemoryNgramStore.from_parquet(str(output_path))
    predictor = KNPredictor(store)
    dist = predictor.distribution(["A"])
    # Unlike the hand-picked fixture above, the real pipeline output also
    # has a "C" -> "A" row (the corpus wraps A B C A B D, so C is really
    # followed by A once), which changes order 2's pooled count-of-counts
    # to n1=3, n2=1 -> D = 3/5 = 0.6: own(B) = (2-0.6)/2 = 0.7,
    # lambda = 0.6*1/2 = 0.3, B = 0.7 + 0.3*0.25 = 0.775.
    assert dist["B"] == pytest.approx(0.775)
    assert sum(dist.values()) == pytest.approx(1.0)

    # `from_rows` also has to accept already-JSON-decoded next/cont dicts
    # (as the pipeline's `next`/`cont` columns are JSON strings, but a
    # caller reading rows back out of `hcg.ngram_histories`'s jsonb columns
    # gets plain dicts).
    rows = pl.read_parquet(output_path).to_dicts()
    for row in rows:
        row["next"] = json.loads(row["next"])
        row["cont"] = json.loads(row["cont"])
    store_from_dicts = InMemoryNgramStore.from_rows(rows)
    assert store_from_dicts.count_of_counts([(0, 2)]) == store.count_of_counts([(0, 2)])
