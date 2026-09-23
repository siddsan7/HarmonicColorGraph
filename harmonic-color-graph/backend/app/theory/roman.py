"""Functional, mode-aware Roman analysis. Rules are applied in documented order."""

from collections.abc import Sequence

from app.schemas.analysis_v2 import (
    AnalysisV2,
    AnalysisWarning,
    KeyProbability,
    Modulation,
    RomanToken,
)
from app.schemas.harmony import CanonicalChord
from app.theory.chord_normalizer import normalize_chord
from app.theory.keys import estimate_keys, estimate_song_keys
from app.theory.progression_normalizer import _tokenize_progression, normalize_progression
from app.theory.relationships_v2 import analyze_relationships
from app.theory.spelling import NOTE_TO_PITCH_CLASS

MAJOR_DEGREES = {
    0: (1, ""),
    1: (2, "b"),
    2: (2, ""),
    3: (3, "b"),
    4: (3, ""),
    5: (4, ""),
    6: (4, "#"),
    7: (5, ""),
    8: (6, "b"),
    9: (6, ""),
    10: (7, "b"),
    11: (7, ""),
}
MINOR_DEGREES = {
    0: (1, ""),
    1: (2, "b"),
    2: (2, ""),
    3: (3, ""),
    4: (3, "#"),
    5: (4, ""),
    6: (4, "#"),
    7: (5, ""),
    8: (6, ""),
    9: (6, "#"),
    10: (7, ""),
    11: (7, ""),
}
NUMERALS = ("I", "II", "III", "IV", "V", "VI", "VII")
MAJOR_DIATONIC = {
    0: {"maj", "maj7", "dom7"},
    2: {"min", "min7"},
    4: {"min", "min7"},
    5: {"maj", "maj7"},
    7: {"maj", "dom7"},
    9: {"min", "min7"},
    11: {"dim", "hdim7", "dim7"},
}
MINOR_DIATONIC = {
    0: {"min", "min7", "minmaj7"},
    2: {"dim", "hdim7", "min", "min7"},
    3: {"maj", "maj7"},
    5: {"min", "min7", "maj", "dom7"},
    7: {"min", "min7", "maj", "dom7"},
    8: {"maj", "maj7"},
    10: {"maj", "dom7"},
    11: {"dim", "hdim7", "dim7"},
}


def parse_key(key: str) -> tuple[int, str, str]:
    parts = key.strip().split()
    if not parts:
        raise ValueError("A key root is required")
    root = parts[0][0].upper() + parts[0][1:]
    mode = parts[1].lower() if len(parts) > 1 else "major"
    if root not in NOTE_TO_PITCH_CLASS or mode not in {"major", "minor"}:
        raise ValueError(f"Unsupported key: {key}")
    return NOTE_TO_PITCH_CLASS[root], mode, f"{root} {mode}"


def _quality_family(chord: CanonicalChord) -> str:
    return chord.quality_class or "maj"


def _degree(root_pc: int, tonic_pc: int, mode: str) -> tuple[int, str]:
    interval = (root_pc - tonic_pc) % 12
    return (MAJOR_DEGREES if mode == "major" else MINOR_DEGREES)[interval]


def _numeral(degree: int, accidental: str, quality: str) -> str:
    lower = quality in {"min", "min7", "minmaj7", "dim", "hdim7", "dim7"}
    numeral = NUMERALS[degree - 1]
    return accidental + (numeral.lower() if lower else numeral)


def _quality_suffix(chord: CanonicalChord) -> str:
    quality = _quality_family(chord)
    if quality == "maj7":
        return "maj7"
    if quality == "minmaj7":
        return "maj7"
    if quality == "dim":
        return "o"
    if quality == "hdim7":
        return "h7"
    if quality == "dim7":
        return "o7"
    if quality in {"dom7", "min7"}:
        return "7"
    if quality == "aug":
        return "+"
    if quality == "sus":
        return "sus2" if chord.intervals[1] == 2 else "sus4"
    if quality == "power":
        return "5"
    return ""


def _figure_parts(chord: CanonicalChord, base: str) -> tuple[str, str]:
    """Return display figure and inversion-free graph core figure."""
    suffix = _quality_suffix(chord)
    core = base + suffix
    if chord.extensions:
        if chord.quality in {"add9", "add11", "add13", "minadd9", "minadd11", "minadd13"}:
            suffix += "add" + chord.extensions[0]
        elif chord.quality in {
            "9",
            "11",
            "13",
            "13b",
            "maj9",
            "maj13",
            "min9",
            "min11",
            "min13",
            "maj9#11",
        }:
            suffix = suffix.removesuffix("7") + chord.quality.removeprefix("min").removeprefix(
                "maj"
            )
            if chord.quality.startswith("maj"):
                suffix = "maj" + suffix.removeprefix("maj")
        else:
            suffix += "".join(chord.extensions)
    inversion = chord.inversion or "root"
    if inversion != "root":
        seventh = _quality_family(chord) in {"dom7", "maj7", "min7", "hdim7", "dim7", "minmaj7"}
        codes = (
            {"first": "65", "second": "43", "third": "42"}
            if seventh
            else {"first": "6", "second": "64"}
        )
        if inversion in codes:
            suffix = codes[inversion] + ("".join(chord.extensions) if chord.extensions else "")
    return base + suffix, core


def _diatonic(chord: CanonicalChord, tonic_pc: int, mode: str) -> bool:
    degree = (chord.root_pc - tonic_pc) % 12
    allowed = MAJOR_DIATONIC if mode == "major" else MINOR_DIATONIC
    quality = _quality_family(chord)
    if quality == "sus" and degree in allowed:
        return True
    if degree == 0 and quality == "dom7":
        return False
    return quality in allowed.get(degree, set())


def _applied_dominant(
    chord: CanonicalChord, next_chord: CanonicalChord | None, tonic_pc: int, mode: str
) -> tuple[str, str, bool] | None:
    quality = _quality_family(chord)
    if quality not in {"maj", "dom7"}:
        return None
    target_pc = (chord.root_pc + 5) % 12
    degree, accidental = _degree(target_pc, tonic_pc, mode)
    if (
        degree == 1
        or accidental
        or (target_pc - tonic_pc) % 12
        not in (MAJOR_DIATONIC if mode == "major" else MINOR_DIATONIC)
    ):
        return None
    if degree == 7:
        return None
    resolved = next_chord is not None and next_chord.root_pc == target_pc
    if quality == "maj" and not resolved:
        return None
    target = _numeral(
        degree,
        accidental,
        "min" if degree in ({2, 3, 6} if mode == "major" else {1, 4, 5}) else "maj",
    )
    return "V", target, not resolved


def _applied_leading_tone(
    chord: CanonicalChord, next_chord: CanonicalChord | None, tonic_pc: int, mode: str
) -> tuple[str, str, bool] | None:
    if _quality_family(chord) not in {"dim", "hdim7", "dim7"}:
        return None
    target_pc = (chord.root_pc + 1) % 12
    degree, accidental = _degree(target_pc, tonic_pc, mode)
    if (
        degree == 1
        or accidental
        or (target_pc - tonic_pc) % 12
        not in (MAJOR_DIATONIC if mode == "major" else MINOR_DIATONIC)
    ):
        return None
    target = _numeral(
        degree,
        accidental,
        "min" if degree in ({2, 3, 6} if mode == "major" else {1, 4, 5}) else "maj",
    )
    resolved = next_chord is not None and next_chord.root_pc == target_pc
    return "vii", target, not resolved


def _tritone_substitute(
    chord: CanonicalChord, next_chord: CanonicalChord | None, tonic_pc: int, mode: str
) -> tuple[str, str | None] | None:
    if _quality_family(chord) != "dom7" or next_chord is None:
        return None
    if (chord.root_pc - next_chord.root_pc) % 12 != 1:
        return None
    if next_chord.root_pc == tonic_pc:
        return "bII", None
    degree, accidental = _degree(next_chord.root_pc, tonic_pc, mode)
    return "subV", _numeral(degree, accidental, _quality_family(next_chord))


def _mixture(chord: CanonicalChord, tonic_pc: int, mode: str) -> str | None:
    interval = (chord.root_pc - tonic_pc) % 12
    quality = _quality_family(chord)
    if mode == "major":
        if (interval, quality) in {(0, "min"), (3, "maj"), (5, "min"), (8, "maj"), (10, "maj")}:
            return "mixolydian" if interval == 10 else "parallel_minor"
        if interval == 2 and quality == "maj":
            return "lydian"
    else:
        if (interval, quality) in {(0, "maj"), (5, "maj"), (9, "maj")}:
            return "dorian" if interval == 5 else "parallel_major"
    return None


def _chromatic_mediant(chord: CanonicalChord, previous: CanonicalChord | None) -> bool:
    if previous is None or _quality_family(chord) not in {"maj", "min"}:
        return False
    if _quality_family(previous) not in {"maj", "min"}:
        return False
    interval = (chord.root_pc - previous.root_pc) % 12
    return (
        interval in {3, 4, 8, 9}
        and len(set(chord.pitch_classes) & set(previous.pitch_classes)) == 1
    )


def romanize_chord(
    chord: CanonicalChord,
    key: str,
    *,
    next_chord: CanonicalChord | None = None,
    previous_chord: CanonicalChord | None = None,
    chord_index: int = 0,
) -> RomanToken:
    tonic_pc, mode, _ = parse_key(key)
    degree, accidental = _degree(chord.root_pc, tonic_pc, mode)
    quality = _quality_family(chord)
    base = _numeral(degree, accidental, quality)
    tags: list[str] = []
    applied_to = None
    applied_role = None
    borrowed_from = None
    chromatic = False
    unresolved = False
    confidence = 1.0

    if _diatonic(chord, tonic_pc, mode):
        pass
    elif applied := _applied_dominant(chord, next_chord, tonic_pc, mode):
        base, applied_to, unresolved = applied
        applied_role = "V"
        tags.append("secondary_dominant")
        confidence = 0.95 if not unresolved else 0.78
    elif applied := _applied_leading_tone(chord, next_chord, tonic_pc, mode):
        base, applied_to, unresolved = applied
        applied_role = "viio"
        tags.append("applied_leading_tone")
        confidence = 0.93 if not unresolved else 0.72
    elif substitute := _tritone_substitute(chord, next_chord, tonic_pc, mode):
        base, applied_to = substitute
        applied_role = "subV"
        tags.append("tritone_substitute")
        confidence = 0.9
    elif (chord.root_pc - tonic_pc) % 12 == 1 and quality == "maj":
        base = "bII"
        tags.append("neapolitan")
        confidence = 0.9
    elif source := _mixture(chord, tonic_pc, mode):
        borrowed_from = source
        tags.append("modal_mixture")
        confidence = 0.88
    elif _chromatic_mediant(chord, previous_chord):
        tags.append("chromatic_mediant")
        chromatic = True
        confidence = 0.72
    else:
        chromatic = True
        confidence = 0.55

    figure, core_figure = _figure_parts(chord, base)
    if applied_to:
        figure += "/" + applied_to
        core_figure += "/" + applied_to
    function = "other"
    if applied_role or base in {"V", "vii"}:
        function = "D"
    elif base in {"I", "i", "vi", "VI", "iii", "III"}:
        function = "T"
    elif base in {"ii", "iio", "IV", "iv", "bII", "bVI"}:
        function = "PD"
    return RomanToken(
        figure=figure,
        display_figure=figure.replace("o", "°").replace("h", "ø"),
        core=("M:" if mode == "major" else "m:") + core_figure,
        mode=mode,
        degree=degree,
        accidental=accidental,
        quality_class=quality,
        inversion=chord.inversion or "root",
        extensions=chord.extensions,
        applied_to=applied_to,
        applied_role=applied_role,
        is_borrowed=borrowed_from is not None,
        borrowed_from=borrowed_from,
        is_chromatic=chromatic,
        function=function,
        confidence=confidence,
        tags=tags,
        unresolved=unresolved,
        root_pc=chord.root_pc,
        bass_pc=chord.bass_pc,
        pitch_classes=chord.pitch_classes,
        chord_index=chord_index,
    )


def analyze_v2(
    chords: str | Sequence[str], key: str | None = None, section_markers: bool = False
) -> AnalysisV2:
    """Analyze a progression, optionally treating pipe markers as section breaks."""
    if isinstance(chords, str):
        raw_sections = chords.split("|") if section_markers else [chords]
    else:
        parts: list[list[str]] = [[]]
        for symbol in chords:
            if section_markers and symbol == "|":
                parts.append([])
            else:
                parts[-1].append(symbol)
        raw_sections = parts
    sections = [normalize_progression(part) for part in raw_sections]
    normalized_chords = [chord for part in sections for chord in part.chords]
    if not normalized_chords:
        raise ValueError("At least one valid chord is required")
    warnings: list[AnalysisWarning] = []
    token_offset = 0
    for raw_section in raw_sections:
        for index, raw_token in enumerate(_tokenize_progression(raw_section)):
            for warning in normalize_chord(raw_token).warnings:
                warnings.append(
                    AnalysisWarning(
                        code=warning.code,
                        message=warning.message,
                        raw_value=warning.raw_value,
                        token_index=token_offset + index,
                    )
                )
        token_offset += len(_tokenize_progression(raw_section))

    if key:
        _, _, song_key = parse_key(key)
        key_distribution = [KeyProbability(key=song_key, probability=1.0)]
        ambiguous = False
        local_keys = [song_key] * len(sections)
        modulations: list[Modulation] = []
    else:
        estimates = estimate_keys(normalized_chords)
        song = estimate_song_keys([part.chords for part in sections])
        song_key = song.song_key
        key_distribution = [
            KeyProbability(key=item.key, probability=item.probability) for item in estimates.top(5)
        ]
        ambiguous = estimates.ambiguous
        local_keys = song.section_keys
        modulations = [
            Modulation(
                section_index=event.section_index,
                from_key=event.from_key,
                to_key=event.to_key,
                semitones=event.semitones,
                description=event.description,
            )
            for event in song.modulations
        ]

    tokens: list[RomanToken] = []
    offset = 0
    for section, local_key in zip(sections, local_keys, strict=True):
        for index, chord in enumerate(section.chords):
            tokens.append(
                romanize_chord(
                    chord,
                    local_key,
                    next_chord=section.chords[index + 1]
                    if index + 1 < len(section.chords)
                    else None,
                    previous_chord=section.chords[index - 1] if index else None,
                    chord_index=offset + index,
                )
            )
        offset += len(section.chords)
    return AnalysisV2(
        key_distribution=key_distribution,
        song_key=song_key,
        ambiguous=ambiguous,
        local_keys=local_keys,
        modulations=modulations,
        tokens=tokens,
        relationships=analyze_relationships(tokens),
        chords=normalized_chords,
        warnings=warnings,
    )
