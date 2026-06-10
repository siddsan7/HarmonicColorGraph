from dataclasses import dataclass

from app.schemas import CanonicalChord, KeyAnalysis, RomanAnalysis
from app.theory.chord_normalizer import NOTE_TO_PITCH_CLASS
from app.theory.progression_normalizer import normalize_progression

MAJOR_SCALE = {0, 2, 4, 5, 7, 9, 11}
MINOR_SCALE = {0, 2, 3, 5, 7, 8, 10}

EXPECTED_MAJOR_QUALITIES = {
    0: "maj",
    2: "min",
    4: "min",
    5: "maj",
    7: "maj",
    9: "min",
    11: "dim",
}

EXPECTED_MINOR_QUALITIES = {
    0: "min",
    2: "dim",
    3: "maj",
    5: "min",
    7: "min",
    8: "maj",
    10: "maj",
}

ROMAN_BY_SEMITONE_MAJOR = {
    0: "I",
    1: "bII",
    2: "II",
    3: "bIII",
    4: "III",
    5: "IV",
    6: "bV",
    7: "V",
    8: "bVI",
    9: "VI",
    10: "bVII",
    11: "VII",
}

ROMAN_BY_SEMITONE_MINOR = {
    0: "I",
    1: "bII",
    2: "II",
    3: "III",
    4: "#III",
    5: "IV",
    6: "bV",
    7: "V",
    8: "VI",
    9: "#VI",
    10: "VII",
    11: "#VII",
}


@dataclass(frozen=True)
class ParsedKey:
    root: str
    mode: str


def analyze_progression(
    chords: str | list[str],
    key: str | None = None,
) -> RomanAnalysis:
    normalized = normalize_progression(chords)
    if key:
        parsed_key = _parse_key(key)
        roman_chords = _romanize_chords(normalized.chords, parsed_key)
        confidence = 1.0 * normalized.chord_parse_success_rate
        return RomanAnalysis(
            key=f"{parsed_key.root} {parsed_key.mode}",
            mode=parsed_key.mode,
            confidence=confidence,
            method="provided_key",
            roman_chords=roman_chords,
            warnings=normalized.warnings,
        )

    candidates = _estimate_keys(normalized.chords)
    best = candidates[0] if candidates else ParsedKey("C", "major")
    alternates = [
        KeyAnalysis(
            key=f"{candidate.root} {candidate.mode}",
            mode=candidate.mode,  # type: ignore[arg-type]
            confidence=_confidence_for_candidate(candidate, normalized.chords),
            method="diatonic_fit_plus_terminal_chord",
            roman_chords=_romanize_chords(normalized.chords, candidate),
        )
        for candidate in candidates[1:3]
    ]
    best_confidence = min(
        _confidence_for_candidate(best, normalized.chords)
        * normalized.chord_parse_success_rate,
        0.99,
    )
    return RomanAnalysis(
        key=f"{best.root} {best.mode}",
        mode=best.mode,  # type: ignore[arg-type]
        confidence=best_confidence,
        method="diatonic_fit_plus_terminal_chord",
        roman_chords=_romanize_chords(normalized.chords, best),
        alternate_analyses=alternates,
        warnings=normalized.warnings,
    )


def _parse_key(key: str) -> ParsedKey:
    parts = key.strip().split()
    root = parts[0].capitalize()
    if len(root) > 1:
        root = root[0].upper() + root[1:]
    mode = parts[1].lower() if len(parts) > 1 else "major"
    if root not in NOTE_TO_PITCH_CLASS:
        raise ValueError(f"Unsupported key root: {key}")
    if mode not in {"major", "minor"}:
        raise ValueError(f"Unsupported key mode: {key}")
    return ParsedKey(root=root, mode=mode)


def _estimate_keys(chords: list[CanonicalChord]) -> list[ParsedKey]:
    candidate_roots = list(dict.fromkeys(chord.root for chord in chords))
    candidates = [
        ParsedKey(root=root, mode=mode)
        for root in candidate_roots
        for mode in ("major", "minor")
    ]
    return sorted(
        candidates,
        key=lambda candidate: _score_candidate(candidate, chords),
        reverse=True,
    )


def _score_candidate(candidate: ParsedKey, chords: list[CanonicalChord]) -> float:
    if not chords:
        return 0.0
    key_pc = NOTE_TO_PITCH_CLASS[candidate.root]
    scale = MAJOR_SCALE if candidate.mode == "major" else MINOR_SCALE
    diatonic_hits = sum(
        1
        for chord in chords
        if (NOTE_TO_PITCH_CLASS[chord.root] - key_pc) % 12 in scale
    )
    score = diatonic_hits / len(chords)
    quality_hits = sum(
        1
        for chord in chords
        if _quality_matches_candidate(
            chord,
            (NOTE_TO_PITCH_CLASS[chord.root] - key_pc) % 12,
            candidate.mode,
        )
    )
    score += 0.20 * (quality_hits / len(chords))

    first_interval = (NOTE_TO_PITCH_CLASS[chords[0].root] - key_pc) % 12
    last_interval = (NOTE_TO_PITCH_CLASS[chords[-1].root] - key_pc) % 12
    if first_interval == 0:
        score += 0.05
    if last_interval == 0:
        score += 0.15
    if candidate.mode == "major" and last_interval == 7:
        score += 0.10
    return score


def _quality_matches_candidate(
    chord: CanonicalChord,
    interval: int,
    mode: str,
) -> bool:
    expected = (
        EXPECTED_MAJOR_QUALITIES
        if mode == "major"
        else EXPECTED_MINOR_QUALITIES
    ).get(interval)
    if expected is None:
        return False
    if expected == "maj":
        return chord.quality in {"maj", "maj7", "7", "sus4", "add9"}
    if expected == "min":
        return chord.quality in {"min", "min7", "min7b5"}
    return chord.quality == expected


def _confidence_for_candidate(
    candidate: ParsedKey,
    chords: list[CanonicalChord],
) -> float:
    score = _score_candidate(candidate, chords)
    return max(0.0, min(score / 1.25, 0.95))


def _romanize_chords(chords: list[CanonicalChord], key: ParsedKey) -> list[str]:
    key_pc = NOTE_TO_PITCH_CLASS[key.root]
    return [_romanize_chord(chord, key_pc, key.mode) for chord in chords]


def _romanize_chord(chord: CanonicalChord, key_pc: int, mode: str) -> str:
    interval = (NOTE_TO_PITCH_CLASS[chord.root] - key_pc) % 12
    base_map = ROMAN_BY_SEMITONE_MAJOR if mode == "major" else ROMAN_BY_SEMITONE_MINOR
    base = base_map[interval]
    roman = _apply_quality_case(base, chord.quality)

    if chord.quality == "maj7":
        return f"{roman}maj7"
    if chord.quality == "min7":
        return f"{roman}7"
    if chord.quality == "7":
        return f"{roman}7"
    if chord.quality == "min7b5":
        return f"{roman}7b5"
    return roman


def _apply_quality_case(base: str, quality: str) -> str:
    if not quality.startswith("min"):
        return base

    accidentals = ""
    numerals = base
    while numerals and numerals[0] in {"b", "#"}:
        accidentals += numerals[0]
        numerals = numerals[1:]
    return f"{accidentals}{numerals.lower()}"
