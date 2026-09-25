"""F40 voicing, motion, parallel-perfect, and playback checks."""

import pytest

from app.theory.voice_leading import (
    generate_voicings,
    transition_metrics,
    voice_lead,
)


@pytest.mark.parametrize("style", ["close", "open", "drop2", "all"])
def test_voicings_have_four_parts_in_range(style):
    voicings = generate_voicings("Cmaj7", style)
    assert voicings
    assert all(len(voicing) == 4 for voicing in voicings)
    assert all(40 <= v[0] <= 62 for v in voicings)
    assert all(48 <= n <= 79 for v in voicings for n in v[1:])
    assert all(v[0] < v[1] < v[2] < v[3] for v in voicings)


def test_slash_chord_bass_is_preserved():
    assert all(v[0] % 12 == 4 for v in generate_voicings("C/E"))


def test_c_to_am_common_tones_and_two_semitone_upper_move():
    metrics = transition_metrics([48, 60, 64, 67], [45, 60, 64, 69], "C", "Am")
    assert metrics.common_tones == 2
    assert sum(abs(n) for n in metrics.motions[1:]) == 2
    assert metrics.parsimonious == "R"


def test_c_to_fm_can_move_a_to_a_flat():
    metrics = transition_metrics([48, 60, 65, 69], [41, 60, 65, 68], "F", "Fm")
    assert -1 in metrics.motions[1:]
    assert metrics.parsimonious == "P"


def test_g7_to_c_resolves_tendency_tones():
    source, target = voice_lead(["G7", "C"])
    assert 71 in source and 65 in source
    assert 72 in target and 64 in target
    metrics = transition_metrics(source, target)
    assert -1 in metrics.motions[1:]  # F→E
    assert 1 in metrics.motions[1:]  # B→C


def test_parallel_fifths_detected_on_root_position_block_chords():
    metrics = transition_metrics([48, 60, 64, 67], [50, 62, 66, 69])
    assert metrics.parallel_perfects >= 1


def test_exhaustive_assignment_finds_crossed_upper_mapping():
    metrics = transition_metrics([48, 60, 64, 67], [48, 67, 60, 64])
    assert metrics.total_motion == 0


@pytest.mark.parametrize(
    "progression",
    [
        ["C", "Am"],
        ["C", "G7", "Am", "F", "C"],
        ["Dm7", "G7", "Cmaj7"],
        ["Ab", "Fm", "Eb", "Bb"],
        ["C/E", "F", "G7", "C"],
    ],
)
def test_smooth_path_never_exceeds_root_position_total_motion(progression):
    smooth = voice_lead(progression, "smooth")
    root = voice_lead(progression, "root_position")

    def cost(path):
        return sum(
            transition_metrics(a, b).total_motion for a, b in zip(path, path[1:], strict=False)
        )

    assert cost(smooth) <= cost(root)
    assert all(len(voicing) == 4 for voicing in smooth)


def test_spread_path_and_invalid_input():
    path = voice_lead(["C", "Am", "F"], "spread")
    assert len(path) == 3
    assert path[0][-1] - path[0][1] >= 12
    with pytest.raises(ValueError):
        voice_lead(["not a chord"])
    with pytest.raises(ValueError):
        voice_lead(["C"], "fast")


def test_metrics_are_nonnegative_and_support_five_voices():
    metrics = transition_metrics([48, 60, 64, 67, 72], [50, 62, 66, 69, 74])
    assert metrics.total_motion >= 0
    assert metrics.max_voice_motion >= 0
    assert metrics.bass_motion >= 0
