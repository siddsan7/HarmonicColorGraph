"""F31: deterministic test-position sampling."""

from __future__ import annotations

from tests.eval.sampling import SampledPosition, sample_test_positions


def _row(song_id, tokens, genre=None, section=None, local_key="C major", ordinal=0):
    return {
        "song_id": song_id,
        "ordinal": ordinal,
        "genre": genre,
        "section": section,
        "local_key": local_key,
        "tokens": tokens,
    }


def test_sampling_never_returns_an_empty_history_position():
    rows = [_row("s1", ["M:I", "M:V", "M:vi"])]
    positions = sample_test_positions(rows, sample_size=100, seed=1)
    assert len(positions) == 2  # positions 1 and 2 only, never position 0
    assert all(p.position >= 1 for p in positions)
    assert all(len(p.history) >= 1 for p in positions)


def test_history_and_actual_token_match_the_source_row():
    rows = [_row("s1", ["M:I", "M:V", "M:vi", "M:IV"])]
    positions = {p.position: p for p in sample_test_positions(rows, sample_size=100, seed=1)}
    assert positions[1].history == ("M:I",)
    assert positions[1].actual == "M:V"
    assert positions[3].history == ("M:I", "M:V", "M:vi")
    assert positions[3].actual == "M:IV"


def test_sampling_is_deterministic_given_the_same_seed():
    rows = [_row(f"s{i}", ["M:I", "M:V", "M:vi", "M:IV", "M:I"]) for i in range(50)]
    first = sample_test_positions(rows, sample_size=20, seed=42)
    second = sample_test_positions(rows, sample_size=20, seed=42)
    assert first == second


def test_different_seeds_usually_sample_differently():
    rows = [_row(f"s{i}", ["M:I", "M:V", "M:vi", "M:IV", "M:I"]) for i in range(50)]
    a = sample_test_positions(rows, sample_size=20, seed=1)
    b = sample_test_positions(rows, sample_size=20, seed=2)
    assert a != b


def test_sample_size_larger_than_available_positions_returns_everything():
    rows = [_row("s1", ["M:I", "M:V"])]  # exactly 1 valid position
    positions = sample_test_positions(rows, sample_size=1000, seed=1)
    assert len(positions) == 1


def test_minor_mode_detected_from_local_key():
    rows = [_row("s1", ["m:i", "m:VII"], local_key="A minor")]
    positions = sample_test_positions(rows, sample_size=10, seed=1)
    assert positions[0].mode == "minor"


def test_missing_local_key_defaults_to_major():
    rows = [_row("s1", ["M:I", "M:V"], local_key=None)]
    positions = sample_test_positions(rows, sample_size=10, seed=1)
    assert positions[0].mode == "major"


def test_depth_bucket_caps_at_four_plus():
    base = SampledPosition(
        song_id="s",
        section_ordinal=0,
        position=0,
        genre=None,
        section=None,
        mode="major",
        history=(),
        actual="M:I",
    )
    assert [
        (base.__class__(**{**base.__dict__, "position": p})).depth_bucket
        for p in (1, 2, 3, 4, 5, 20)
    ] == ["1", "2", "3", "4+", "4+", "4+"]
