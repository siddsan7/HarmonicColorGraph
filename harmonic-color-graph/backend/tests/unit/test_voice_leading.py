"""F40 voicing, motion, parallel-perfect, and playback checks."""

from itertools import combinations_with_replacement, permutations, product

import pytest

import app.theory.voice_leading as voice_leading
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


def _exhaustive_assignment(source, target):
    return min(
        permutations(target[1:]),
        key=lambda upper: (
            sum(abs(a - b) for a, b in zip(source[1:], upper, strict=True)),
            max(abs(a - b) for a, b in zip(source[1:], upper, strict=True)),
            upper,
        ),
    )


def test_ordered_assignment_matches_exhaustive_with_ties_and_crossed_targets():
    # Include repeated pitches, crossed targets, tied motions, and every
    # supported voice count. Compare the assigned notes, not just the cost.
    pitches = (48, 60, 64, 67)
    for size in range(1, 5):
        for upper_source in combinations_with_replacement(pitches, size):
            for upper_target in product(pitches, repeat=size):
                source, target = (40, *upper_source), (43, *upper_target)
                assert voice_leading._best_assignment(source, target) == _exhaustive_assignment(
                    source, target
                )


def test_crossed_source_keeps_exhaustive_assignment():
    for source_upper in permutations((60, 64, 67, 72)):
        for target_upper in permutations((59, 65, 69, 74)):
            source, target = (48, *source_upper), (50, *target_upper)
            assert voice_leading._best_assignment(source, target) == _exhaustive_assignment(
                source, target
            )


def test_smooth_paths_match_exhaustive_assignment(monkeypatch):
    progressions = [
        ["Cmaj7", "Am7", "Dm7", "G7", "Cmaj7"],
        ["C/E", "Fm/Ab", "G7/B", "C"],
        ["F#dim7", "Gm", "Ebmaj7", "D7"],
        ["Csus2", "Dsus4", "G", "C"],
    ]
    optimized = [voice_lead(chords) for chords in progressions]
    monkeypatch.setattr(voice_leading, "_best_assignment", _exhaustive_assignment)
    assert optimized == [voice_lead(chords) for chords in progressions]
