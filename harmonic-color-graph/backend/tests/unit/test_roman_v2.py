"""Gold, rule-order, transposition, and throughput checks for F12."""

import json
import re
import time
from collections import defaultdict
from pathlib import Path

import pytest

from app.theory.keys import CANONICAL_TONIC_NAME
from app.theory.roman import analyze_v2
from app.theory.spelling import NOTE_TO_PITCH_CLASS

GOLD = Path(__file__).resolve().parents[3] / "data/gold/roman.jsonl"


def _rows() -> list[dict]:
    return [json.loads(line) for line in GOLD.read_text(encoding="utf-8").splitlines()]


def test_gold_roman_core_and_figure_accuracy():
    rows = _rows()
    assert len(rows) >= 60
    figure_hits = core_hits = total = 0
    for row in rows:
        result = analyze_v2(row["chords"], row["key"])
        for token, figure, core in zip(result.tokens, row["figures"], row["cores"], strict=True):
            figure_hits += token.figure == figure
            core_hits += token.core == core
            total += 1
    assert core_hits / total >= 0.95
    assert figure_hits / total >= 0.90


def test_transposition_preserves_core_tokens():
    groups = defaultdict(list)
    for row in _rows():
        groups[row["template"]].append(row)
    for group in groups.values():
        assert len(group) == 3
        token_sets = [
            [token.core for token in analyze_v2(row["chords"], row["key"]).tokens] for row in group
        ]
        assert token_sets[0] == token_sets[1] == token_sets[2]


def test_applied_dominant_core_is_invariant_in_all_twelve_keys():
    expected = ["M:V7/V", "M:V", "M:I"]
    for shift in range(12):
        key_root = CANONICAL_TONIC_NAME[shift]
        chords = []
        for symbol in ("D7", "G", "C"):
            match = re.fullmatch(r"([A-G][#b]?)(.*)", symbol)
            assert match is not None
            root, quality = match.groups()
            chords.append(CANONICAL_TONIC_NAME[(NOTE_TO_PITCH_CLASS[root] + shift) % 12] + quality)
        assert [token.core for token in analyze_v2(chords, f"{key_root} major").tokens] == expected


@pytest.mark.parametrize(
    "chords,key,figures",
    [
        (["D7", "G", "C"], "C major", ["V7/V", "V", "I"]),
        (["E7", "Am"], "C major", ["V7/vi", "vi"]),
        (["Fm", "C"], "C major", ["iv", "I"]),
        (["Bdim", "C"], "C major", ["viio", "I"]),
        (["Cmaj9", "Fadd9", "Gsus4", "C"], "C major", ["Imaj9", "IVadd9", "Vsus4", "I"]),
        (["C", "C/E", "F", "G"], "C major", ["I", "I6", "IV", "V"]),
        (["Db7", "C"], "C major", ["bII7", "I"]),
    ],
)
def test_functional_rule_cases(chords, key, figures):
    assert [token.figure for token in analyze_v2(chords, key).tokens] == figures


def test_display_figures_use_music_symbols_while_core_stays_ascii():
    diminished = analyze_v2(["Bdim", "C"], "C major").tokens[0]
    half_diminished = analyze_v2(["Bm7b5", "E7", "Am"], "A minor").tokens[0]
    assert diminished.figure == "viio"
    assert diminished.display_figure == "vii°"
    assert half_diminished.display_figure.endswith("ø7")


@pytest.mark.slow
def test_throughput_at_least_1000_sections_per_second():
    count = 1_000
    start = time.perf_counter()
    for _ in range(count):
        analyze_v2(["D7", "G", "C", "Am"], "C major")
    assert count / (time.perf_counter() - start) >= 1_000
