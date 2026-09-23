from dataclasses import dataclass

from app.schemas import CanonicalChord, KeyAnalysis, RomanAnalysis
from app.theory.chord_normalizer import NOTE_TO_PITCH_CLASS
from app.theory.keys import estimate_keys
from app.theory.progression_normalizer import normalize_progression

KEY_ESTIMATION_METHOD = "pitch_class_profile_v2"

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
            ambiguous=False,
        )

    key_result = estimate_keys(normalized.chords)
    best = _parsed_key_from_estimate(key_result.best.key, key_result.best.mode)
    alternates = [
        KeyAnalysis(
            key=estimate.key,
            mode=estimate.mode,  # type: ignore[arg-type]
            confidence=estimate.probability,
            method=KEY_ESTIMATION_METHOD,
            roman_chords=_romanize_chords(
                normalized.chords, _parsed_key_from_estimate(estimate.key, estimate.mode)
            ),
        )
        for estimate in key_result.top(3)[1:3]
    ]
    best_confidence = min(
        key_result.best.probability * normalized.chord_parse_success_rate,
        0.99,
    )
    return RomanAnalysis(
        key=key_result.best.key,
        mode=key_result.best.mode,  # type: ignore[arg-type]
        confidence=best_confidence,
        method=KEY_ESTIMATION_METHOD,
        roman_chords=_romanize_chords(normalized.chords, best),
        alternate_analyses=alternates,
        warnings=normalized.warnings,
        ambiguous=key_result.ambiguous,
    )


def _parsed_key_from_estimate(key: str, mode: str) -> "ParsedKey":
    return ParsedKey(root=key.split()[0], mode=mode)


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
