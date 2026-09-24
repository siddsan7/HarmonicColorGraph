"""F22 `ngrams` stage: raw (context, order, history) counts and Kneser-Ney
continuation counts, hand-verified against a small token sequence.
"""

import json
from pathlib import Path

import pytest

pl = pytest.importorskip("polars")

from pipeline.stages.analyze import SECTIONS_SCHEMA  # noqa: E402
from pipeline.stages.ngrams import run_ngrams  # noqa: E402


def _section_row(song_index, tokens, genre=None, section=None, decade=None):
    return {
        "song_index": song_index,
        "song_id": str(song_index),
        "ordinal": 0,
        "section": section,
        "local_key": "C major",
        "key_conf": 0.9,
        "ambiguous": False,
        "tokens": tokens,
        "figures": tokens,
        "chords": ["C:maj"] * len(tokens),
        "labels": [],
        "genre": genre,
        "decade": decade,
        "spotify_id": None,
        "split": "train",
        "repeat_count": 1,
    }


def _write_fixture(path: Path, rows: list[dict]) -> Path:
    pl.DataFrame(rows, schema=SECTIONS_SCHEMA).write_parquet(path)
    return path


def _rows_by_key(output_path: Path) -> dict[tuple[str, int, str], dict]:
    frame = pl.read_parquet(output_path)
    return {(r["context"], r["order"], r["history"]): r for r in frame.to_dicts()}


def test_raw_counts_and_continuation_counts_on_a_hand_worked_example(tmp_path: Path):
    # A B C A B D -- worked by hand in the PR description / commit message.
    rows = [_section_row(0, ["A", "B", "C", "A", "B", "D"])]
    sections_path = _write_fixture(tmp_path / "sections.parquet", rows)
    output_path = tmp_path / "ngrams.parquet"

    summary = run_ngrams(sections_path, output_path)

    assert summary.contexts == ["global"]
    by_key = _rows_by_key(output_path)

    order1 = by_key[("global", 1, "")]
    assert json.loads(order1["next"]) == {"A": 2, "B": 2, "C": 1, "D": 1}
    assert order1["total"] == 6
    assert order1["distinct_next"] == 4

    order2_a = by_key[("global", 2, "A")]
    assert json.loads(order2_a["next"]) == {"B": 2}
    assert json.loads(order2_a["cont"]) == {"B": 1}  # only ("C","A") precedes history "A"

    order2_b = by_key[("global", 2, "B")]
    assert json.loads(order2_b["next"]) == {"C": 1, "D": 1}
    assert json.loads(order2_b["cont"]) == {"C": 1, "D": 1}  # only ("A","B") precedes history "B"

    # Both order-3 histories here occur only once (total 2 < the order-3
    # prune threshold of 3), so neither survives to the output -- covered
    # by test_pruning_drops_low_total_higher_order_histories below.
    assert ("global", 3, "A B") not in by_key


def test_max_order_history_has_no_continuation_counts(tmp_path: Path):
    # A history at a context's own max order has no order+1 data to derive
    # continuation counts from, so its cont dict is always empty. Order 3 is
    # the max for a non-global context (section:verse), unlike global (5).
    tokens = [
        "A",
        "B",
        "C",
    ] * 4  # order-3 history "A B" recurs 4 times, clears the order-3 prune bar
    rows = [_section_row(0, tokens, section="verse")]
    sections_path = _write_fixture(tmp_path / "sections.parquet", rows)
    output_path = tmp_path / "ngrams.parquet"

    run_ngrams(
        sections_path,
        output_path,
        min_context_observations=1,
        prune_min_total={3: 3, 4: 5, 5: 8},
    )

    by_key = _rows_by_key(output_path)
    order3_ab = by_key[("section:verse", 3, "A B")]
    assert json.loads(order3_ab["next"]) == {"C": 4}
    assert json.loads(order3_ab["cont"]) == {}


def test_max_order_is_5_for_global_and_3_for_other_contexts(tmp_path: Path):
    # A periodic pattern repeated enough times that even order-5 histories
    # (prune threshold: total >= 8) survive to the output.
    tokens = ["A", "B", "C", "D", "E", "F"] * 10
    rows = [_section_row(0, tokens, genre="pop")]
    sections_path = _write_fixture(tmp_path / "sections.parquet", rows)
    output_path = tmp_path / "ngrams.parquet"

    run_ngrams(
        sections_path,
        output_path,
        min_context_observations=1,
        prune_min_total={3: 3, 4: 5, 5: 8},
    )

    frame = pl.read_parquet(output_path)
    assert frame.filter(pl.col("context") == "global")["order"].max() == 5
    assert frame.filter(pl.col("context") == "genre:pop")["order"].max() == 3


def test_small_contexts_are_dropped_global_always_kept(tmp_path: Path):
    # Same "contexts worth modeling" threshold as aggregate's TRANSITIONS_TO:
    # a context with too few bigram-level observations gets no n-gram rows
    # at all (not just per-row pruning), keeping ngrams and aggregate
    # consistent about what counts as a real context.
    rows = [_section_row(0, ["A", "B", "C"], genre="obscure")]
    sections_path = _write_fixture(tmp_path / "sections.parquet", rows)
    output_path = tmp_path / "ngrams.parquet"

    summary = run_ngrams(sections_path, output_path, min_context_observations=2000)

    assert summary.contexts == ["global"]
    frame = pl.read_parquet(output_path)
    assert set(frame["context"].unique().to_list()) == {"global"}


def test_pruning_drops_low_total_higher_order_histories(tmp_path: Path):
    # Order-3 histories that occur only once should be pruned (threshold 3);
    # order 1-2 histories are never pruned regardless of how rare.
    rows = [_section_row(i, ["A", "B", "C", "D"]) for i in range(2)]
    sections_path = _write_fixture(tmp_path / "sections.parquet", rows)
    output_path = tmp_path / "ngrams.parquet"

    summary = run_ngrams(sections_path, output_path)

    frame = pl.read_parquet(output_path)
    assert frame.filter(pl.col("order") == 3).height == 0
    assert summary.rows_pruned > 0
    assert frame.filter(pl.col("order") == 1).height >= 1
    assert frame.filter(pl.col("order") == 2).height >= 1


def test_continuation_counts_never_negative_and_next_totals_match(tmp_path: Path):
    rows = [
        _section_row(0, ["M:I", "M:IV", "M:V", "M:I", "M:vi", "M:IV", "M:V", "M:I"]),
    ]
    sections_path = _write_fixture(tmp_path / "sections.parquet", rows)
    output_path = tmp_path / "ngrams.parquet"

    run_ngrams(sections_path, output_path)

    frame = pl.read_parquet(output_path)
    for row in frame.to_dicts():
        next_counts = json.loads(row["next"])
        cont_counts = json.loads(row["cont"])
        assert sum(next_counts.values()) == row["total"]
        assert len(next_counts) == row["distinct_next"]
        assert all(v >= 0 for v in cont_counts.values())


def test_budget_estimate_is_measured_not_zero(tmp_path: Path):
    rows = [
        _section_row(0, ["M:I", "M:IV", "M:V", "M:I", "M:vi", "M:IV", "M:V", "M:I"]),
    ]
    sections_path = _write_fixture(tmp_path / "sections.parquet", rows)
    output_path = tmp_path / "ngrams.parquet"

    summary = run_ngrams(sections_path, output_path)

    assert summary.budget_estimate_mb > 0
