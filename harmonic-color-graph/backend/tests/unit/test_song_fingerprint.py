"""Offline song-fingerprint prototype (`pipeline/song_fingerprint.py`)."""

import json

import numpy as np
import pytest

pytest.importorskip("scipy")
pytest.importorskip("sklearn")

from app.color.features import AXES  # noqa: E402
from app.color.perceptual import PERCEPTUAL_AXES  # noqa: E402
from pipeline.song_fingerprint import (  # noqa: E402
    ARC_AXES,
    SongIndex,
    camelot,
    compatible_camelot,
    fingerprint_song,
    proxy_metrics,
    song_embedding,
)


def _section(ordinal, section, key, chords, repeat=1):
    return {
        "ordinal": ordinal,
        "section": section,
        "local_key": key,
        "key_conf": 0.9,
        "chords": chords,
        "genre": "pop",
        "repeat_count": repeat,
    }


POP_C = [
    _section(0, "verse", "C major", ["C:maj", "G:maj", "A:min", "F:maj"], repeat=2),
    _section(1, "chorus", "C major", ["F:maj", "G:maj", "C:maj", "A:min", "F:maj", "G:maj"]),
]
POP_D = [
    _section(0, "verse", "D major", ["D:maj", "A:maj", "B:min", "G:maj"], repeat=2),
    _section(1, "chorus", "D major", ["G:maj", "A:maj", "D:maj", "B:min", "G:maj", "A:maj"]),
]
BORROWED_C = [
    _section(0, "verse", "C major", ["C:maj", "F:min", "C:maj", "Ab:maj", "Bb:maj", "C:maj"]),
    _section(1, "chorus", "C major", ["Ab:maj", "Bb:maj", "C:maj", "F:min", "C:maj"]),
]
MINOR_A = [
    _section(0, "verse", "A minor", ["A:min", "F:maj", "C:maj", "G:maj"], repeat=2),
    _section(1, None, "A minor", ["A:min", "D:min", "E:7", "A:min"]),
]


@pytest.mark.parametrize(
    ("key", "code"),
    [
        ("C major", "8B"),
        ("A minor", "8A"),
        ("G major", "9B"),
        ("F major", "7B"),
        ("B major", "1B"),
        ("Ab minor", "1A"),
        ("F# minor", "11A"),
        ("Bb major", "6B"),
        ("E major", "12B"),
    ],
)
def test_camelot_matches_the_dj_key_wheel(key, code):
    assert camelot(key) == code


def test_compatible_camelot_wraps_around_the_wheel():
    assert compatible_camelot("12B") == {"12B", "12A", "1B", "11B"}
    assert compatible_camelot("1A") == {"1A", "1B", "2A", "12A"}


def test_fingerprint_reports_every_axis_key_and_arc():
    fingerprint = fingerprint_song(POP_C)
    assert fingerprint["key"] == "C major"
    assert fingerprint["camelot"] == "8B"
    assert fingerprint["n_positions"] == 10
    for axis in AXES:
        if axis != "surprise":  # needs the n-gram predictor
            assert fingerprint[f"raw_{axis}"] is not None
    assert fingerprint["raw_surprise"] is None
    for axis in PERCEPTUAL_AXES:
        assert 0.0 <= fingerprint[f"perc_{axis}"] <= 1.0
    assert all(fingerprint[f"arc_{axis}"] is not None for axis in ARC_AXES)
    # the verse repeats twice, so its tokens count double
    assert json.loads(fingerprint["token_counts"])["M:I"] == 3


def test_fingerprint_is_the_same_in_another_key_except_for_the_key_itself():
    in_c, in_d = fingerprint_song(POP_C), fingerprint_song(POP_D)
    assert (in_c["camelot"], in_d["camelot"]) == ("8B", "10B")
    for name, value in in_c.items():
        if name in {"key", "camelot"}:
            continue
        assert in_d[name] == pytest.approx(value), name


def test_fingerprint_has_no_arc_without_both_verse_and_chorus():
    fingerprint = fingerprint_song(MINOR_A)
    assert fingerprint["mode"] == "minor"
    assert all(fingerprint[f"arc_{axis}"] is None for axis in ARC_AXES)


def test_fingerprint_is_none_when_nothing_can_be_analyzed():
    assert fingerprint_song([_section(0, "verse", None, ["C:maj"])]) is None
    assert fingerprint_song([]) is None


def test_borrowed_chords_raise_nostalgia_and_chromaticity():
    plain, borrowed = fingerprint_song(POP_C), fingerprint_song(BORROWED_C)
    assert borrowed["perc_nostalgia"] > plain["perc_nostalgia"]
    assert borrowed["raw_chromaticity"] > plain["raw_chromaticity"]


def test_song_embedding_weights_rare_tokens_and_normalizes():
    vectors = {"a": np.array([1.0, 0.0]), "b": np.array([0.0, 1.0])}
    frequency = {"a": 0.9, "b": 0.001}
    vector = song_embedding({"a": 1, "b": 1, "unknown": 5}, vectors, frequency)
    assert np.linalg.norm(vector) == pytest.approx(1.0)
    assert vector[1] > vector[0]
    assert song_embedding({"unknown": 1}, vectors, frequency) is None


def _row(song_id, sections, artist, genre):
    fingerprint = fingerprint_song(sections)
    counts = json.loads(fingerprint["token_counts"])
    tokens = sorted(counts)
    vector = np.array([counts.get(token, 0) for token in ALL_TOKENS], dtype=np.float32)
    assert tokens
    return {
        "song_id": song_id,
        "spotify_id": f"sp{song_id}",
        "genre": genre,
        "decade": "2010.0",
        "artist_id": artist,
        "main_genre": genre,
        "genre_tags": json.dumps([genre]),
        **fingerprint,
        "embed": (vector / np.linalg.norm(vector)).tolist(),
    }


ALL_TOKENS = sorted(
    {
        token
        for song in (POP_C, POP_D, BORROWED_C, MINOR_A)
        for token in json.loads(fingerprint_song(song)["token_counts"])
    }
)


@pytest.fixture
def index():
    return SongIndex(
        [
            _row("pop-c", POP_C, "artist-1", "pop"),
            _row("pop-d", POP_D, "artist-2", "pop"),
            _row("borrowed", BORROWED_C, "artist-3", "rock"),
            _row("minor", MINOR_A, "artist-1", "rock"),
        ]
    )


def test_the_transposed_copy_is_the_nearest_neighbour(index):
    neighbours = index.neighbours("pop-c", k=3)
    assert neighbours[0]["song_id"] == "pop-d"
    # same-artist songs are left out by default
    assert "minor" not in [row["song_id"] for row in neighbours]
    assert "minor" in [
        row["song_id"] for row in index.neighbours("pop-c", k=3, exclude_same_artist=False)
    ]


def test_camelot_filter_keeps_only_mix_compatible_keys(index):
    # C major (8B) against D major (10B): two steps apart, not compatible
    compatible = index.neighbours("pop-c", k=3, camelot_compatible=True)
    assert [row["song_id"] for row in compatible] == ["borrowed"]


def test_arc_weight_is_ignored_for_songs_without_an_arc(index):
    weights = {"color": 0.0, "embed": 0.0, "pattern": 0.0, "arc": 1.0}
    scores = index.blended([index.position["minor"]], weights)
    assert np.allclose(scores, 0.0)


def test_proxy_metrics_report_every_arm(index):
    report = proxy_metrics(index, queries=4, k=1)
    assert set(report["arms"]) == {"color", "embed", "pattern", "arc", "blend", "random"}
    assert report["arms"]["blend"]["same_main_genre"]["queries"] == 4
