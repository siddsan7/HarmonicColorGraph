"""Gold, calibration, invariance, and modulation checks for F11."""

import json
import re
from pathlib import Path

import pytest

from app.theory.chord_normalizer import normalize_chord
from app.theory.keys import CANONICAL_TONIC_NAME, estimate_keys, estimate_song_keys
from app.theory.spelling import NOTE_TO_PITCH_CLASS
from pipeline.stages.calibrate_keys import expected_calibration_error

GOLD = Path(__file__).resolve().parents[3] / "data/gold/keys.jsonl"


def _chords(symbols: list[str]) -> list:
    return [normalize_chord(symbol).chord for symbol in symbols]


def test_held_out_gold_key_metrics():
    rows = [json.loads(line) for line in GOLD.read_text(encoding="utf-8").splitlines()]
    held_out = [
        row
        for row in rows
        if (row.get("key") or row["acceptable_keys"][0]).split()[0] in {"Eb", "A"}
    ]
    top1 = top2 = accepted = 0
    calibration = []
    for row in held_out:
        result = estimate_keys(_chords(row["chords"]))
        targets = set(row.get("acceptable_keys", [row.get("key")]))
        correct = result.best.key in targets
        top1 += correct
        top2 += bool({item.key for item in result.top(2)} & targets)
        if "acceptable_keys" in row:
            accepted += bool({item.key for item in result.top(2)} & targets)
        calibration.append((result.best.probability, correct))
    assert len(held_out) == 40
    assert top1 / len(held_out) >= 0.80
    assert top2 / len(held_out) >= 0.90
    assert expected_calibration_error(calibration) < 0.10
    assert accepted / sum("acceptable_keys" in row for row in held_out) >= 0.90


def test_tonic_absent_and_open_loop_are_ambiguous():
    tonic_absent = estimate_keys(_chords(["Dm", "G"]))
    assert "C major" in {item.key for item in tonic_absent.top(2)}
    assert tonic_absent.ambiguous
    assert estimate_keys(_chords(["C", "Am", "F", "G"])).ambiguous


def test_minor_plagal_can_identify_major_tonic():
    assert estimate_keys(_chords(["Fm", "C"])).best.key == "C major"


@pytest.mark.parametrize("template", ["diatonic_major_cadence", "minor_harmonic_v", "jazz_ii_v_i"])
def test_transposed_template_confidences_are_invariant(template):
    rows = [json.loads(line) for line in GOLD.read_text(encoding="utf-8").splitlines()]
    group = [row for row in rows if row["template"] == template]
    assert len(group) == 4
    distributions = [estimate_keys(_chords(row["chords"])) for row in group]
    for result in distributions[1:]:
        for first, other in zip(distributions[0].estimates, result.estimates, strict=True):
            assert first.probability == pytest.approx(other.probability, abs=1e-9)


def test_song_key_and_local_modulation():
    sections = [
        _chords(["C", "F", "G", "C"]),
        _chords(["C", "F", "G", "C"]),
        _chords(["D", "G", "A", "D"]),
    ]
    result = estimate_song_keys(sections)
    assert result.song_key == "C major"
    assert len(result.section_keys) == 3
    assert result.section_keys[2] == "D major"
    assert result.modulations[0].section_index == 2
    assert result.modulations[0].semitones == 2


def test_section_consensus_resolves_major_key_against_plagal_tonic_bias():
    # Synthetic D-major song: F#m is diatonic iii, not G-major vii diminished.
    sections = [
        _chords("D Bm A G D".split()),
        _chords("Bm F#m G D".split()),
        _chords("D Bm F#m Gmaj7 G".split()),
    ]
    assert estimate_keys([chord for section in sections for chord in section]).best.key == "G major"
    result = estimate_song_keys(sections)
    assert result.song_key == "D major"
    assert result.song_key_estimate.best.key == result.song_key
    assert result.section_estimates[-1].best.key == "G major"
    assert result.section_keys == ["D major"] * 3


def test_section_consensus_keeps_natural_minor_bridge_diatonic():
    # Synthetic A-minor song: Em is natural-minor v, not F-major vii diminished.
    sections = [
        _chords("F Am Dm Am".split()),
        _chords("Am Dm F Am".split()),
        _chords("F Em Am C F".split()),
        _chords("F Dm Am C".split()),
    ]
    assert estimate_keys([chord for section in sections for chord in section]).best.key == "C major"
    result = estimate_song_keys(sections)
    assert result.song_key == "A minor"
    assert result.song_key_estimate.best.key == result.song_key
    assert result.section_estimates[2].best.key == "F major"
    assert result.section_keys == ["A minor", "A minor", "A minor", "C major"]


def test_unsectioned_progression_reports_internal_modulation():
    # Three invented cadence regions in one source section.
    chords = _chords("E B7 E A E Ab Eb7 Ab Db Ab C G7 C F C".split())
    result = estimate_song_keys([chords])
    assert [(r.start, r.end, r.key) for r in result.section_regions[0]] == [
        (0, 5, "E major"),
        (5, 10, "Ab major"),
        (10, 15, "C major"),
    ]
    assert [(e.chord_index, e.from_key, e.to_key) for e in result.modulations] == [
        (5, "E major", "Ab major"),
        (10, "Ab major", "C major"),
    ]


@pytest.mark.parametrize(
    "text",
    [
        "C F G C Am D7 G C C F G C",
        "C Am F G C Am F G C Am F G",
        "Am Dm E7 Am F Dm E7 Am",
        "C F Fm C G C F Fm C G C",
    ],
)
def test_tonicizations_and_borrowed_chords_do_not_split_keys(text):
    result = estimate_song_keys([_chords(text.split())])
    assert len(result.section_regions[0]) == 1
    assert result.modulations == []


@pytest.mark.parametrize("minor", [False, True])
def test_internal_regions_are_transposition_invariant(minor):
    template = (
        "Am E7 Am Dm Am Cm G7 Cm Fm Cm Em B7 Em Am Em"
        if minor
        else "E B7 E A E Ab Eb7 Ab Db Ab C G7 C F C"
    )
    reference = estimate_song_keys([_chords(template.split())]).section_regions[0]
    assert len(reference) == 3
    for shift in range(12):
        symbols = []
        for symbol in template.split():
            match = re.fullmatch(r"([A-G][#b]?)(.*)", symbol)
            root, quality = match.groups()
            symbols.append(CANONICAL_TONIC_NAME[(NOTE_TO_PITCH_CLASS[root] + shift) % 12] + quality)
        result = estimate_song_keys([_chords(symbols)]).section_regions[0]
        assert [(r.start, r.end) for r in result] == [(0, 5), (5, 10), (10, 15)]
        for before, after in zip(reference, result, strict=True):
            assert after.key.split()[1] == before.key.split()[1]
            assert (
                NOTE_TO_PITCH_CLASS[after.key.split()[0]]
                == (NOTE_TO_PITCH_CLASS[before.key.split()[0]] + shift) % 12
            )
            assert after.confidence == pytest.approx(before.confidence, abs=1e-9)


def test_modulations_include_section_entry_and_return_after_internal_change():
    result = estimate_song_keys(
        [
            _chords("C F G C".split() * 2),
            _chords("D G A D".split() * 2 + "E A B E".split() * 2),
            _chords("C F G C".split() * 2),
        ]
    )
    assert [(e.chord_index, e.from_key, e.to_key) for e in result.modulations] == [
        (8, "C major", "D major"),
        (16, "D major", "E major"),
        (24, "E major", "C major"),
    ]


@pytest.mark.parametrize("template", [["C", "F", "G", "C"], ["Am", "Dm", "E7", "Am"]])
def test_all_twelve_transpositions_preserve_confidences(template):
    reference = None
    for shift in range(12):
        symbols = []
        for symbol in template:
            match = re.fullmatch(r"([A-G][#b]?)(.*)", symbol)
            assert match is not None
            root, quality = match.groups()
            new_root = CANONICAL_TONIC_NAME[(NOTE_TO_PITCH_CLASS[root] + shift) % 12]
            symbols.append(new_root + quality)
        result = estimate_keys(_chords(symbols))
        confidences = [item.probability for item in result.estimates]
        if reference is None:
            reference = confidences
        else:
            assert confidences == pytest.approx(reference, abs=1e-9)
