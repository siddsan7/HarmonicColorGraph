"""Dev-only independent music21 comparisons for key and Roman gold fixtures."""

import json
from pathlib import Path

from app.theory.chord_normalizer import normalize_chord
from app.theory.keys import CANONICAL_TONIC_NAME, estimate_keys
from app.theory.roman import analyze_v2

ROOT = Path(__file__).resolve().parents[2]


def _read(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _chords(row: dict) -> list:
    chords = [normalize_chord(symbol).chord for symbol in row["chords"]]
    if any(chord is None for chord in chords):
        raise ValueError(f"Unparseable gold row: {row}")
    return chords


def compare_keys() -> tuple[int, int, list[str]]:
    from music21 import chord as m21_chord
    from music21 import stream

    rows = _read(ROOT / "data/gold/keys.jsonl")
    agree = 0
    differences = []
    for row in rows:
        chords = _chords(row)
        sequence = stream.Stream()
        for item in chords:
            sequence.append(m21_chord.Chord(item.tones_spelled[:4]))
        oracle = sequence.analyze("key")
        oracle_pc = int(oracle.tonic.pitchClass)
        oracle_label = f"{CANONICAL_TONIC_NAME[oracle_pc]} {oracle.mode}"
        ours = estimate_keys(chords).best.key
        if ours == oracle_label:
            agree += 1
        else:
            differences.append(
                f"{row['template']} {row['chords']}: ours {ours}; music21 {oracle_label}"
            )
    return agree, len(rows), differences


def compare_roman_diatonic() -> tuple[int, int, list[str]]:
    from music21 import chord as m21_chord
    from music21 import key as m21_key
    from music21 import roman as m21_roman

    rows = _read(ROOT / "data/gold/roman.jsonl")
    agree = 0
    total = 0
    differences = []
    for row in rows:
        ours = analyze_v2(row["chords"], row["key"])
        tonic, mode = row["key"].split()
        oracle_key = m21_key.Key(tonic, "minor" if mode == "minor" else "major")
        for symbol, chord, token in zip(row["chords"], ours.chords, ours.tokens, strict=True):
            if token.is_chromatic or token.is_borrowed or token.applied_to or token.tags:
                continue
            # The oracle comparison is degree+triad quality. music21 and our
            # graph contract intentionally display seventh and inversion
            # suffixes differently, so those are evaluated by the gold figures.
            oracle = m21_roman.romanNumeralFromChord(
                m21_chord.Chord(chord.tones_spelled[:4]), oracle_key
            )
            total += 1
            oracle_degree = int(oracle.scaleDegree)
            oracle_minor = oracle.quality in {"minor", "diminished", "half-diminished"}
            ours_minor = token.quality_class in {"min", "min7", "minmaj7", "dim", "dim7", "hdim7"}
            if token.degree == oracle_degree and ours_minor == oracle_minor:
                agree += 1
            else:
                differences.append(
                    f"{row['key']} {symbol}: ours {token.figure} (degree {token.degree}), "
                    f"music21 {oracle.figure} (degree {oracle_degree}); "
                    "enharmonic or contextual quality interpretation differs"
                )
    return agree, total, differences


def main() -> None:
    key_agree, key_total, key_differences = compare_keys()
    roman_agree, roman_total, roman_differences = compare_roman_diatonic()
    key_report = ROOT / "docs/eval/keys.md"
    with key_report.open("a", encoding="utf-8") as handle:
        handle.write("\n## music21 oracle\n\n")
        handle.write(
            f"Top-1 exact-key agreement: {key_agree}/{key_total} "
            f"({key_agree / key_total:.1%}). The oracle is a comparison, "
            "not a gold target.\n\n"
        )
        handle.write("\n".join(f"- {item}" for item in key_differences[:30]) + "\n")
    roman_report = ROOT / "docs/eval/roman.md"
    roman_report.write_text(
        "# Roman Analysis v2 Evaluation\n\n"
        f"music21 diatonic degree/triad-quality agreement: {roman_agree}/{roman_total} "
        f"({roman_agree / roman_total:.1%}).\n\n"
        "The comparison omits applied, borrowed, and chromatic chords because "
        "their interpretations depend on local progression context. The gold "
        "figures test those cases directly.\n\n"
        "## Disagreements\n\n"
        + ("\n".join(f"- {item}" for item in roman_differences) or "None.")
        + "\n",
        encoding="utf-8",
    )
    print(f"key oracle {key_agree}/{key_total}; roman oracle {roman_agree}/{roman_total}")


if __name__ == "__main__":
    main()
