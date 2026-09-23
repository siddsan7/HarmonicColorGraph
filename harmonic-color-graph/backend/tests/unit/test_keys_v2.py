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
