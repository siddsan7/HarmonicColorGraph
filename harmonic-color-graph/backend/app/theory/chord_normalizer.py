import re
from dataclasses import dataclass

from app.schemas import CanonicalChord, ChordNormalizationResult, ParseWarning

NOTE_TO_PITCH_CLASS = {
    "C": 0,
    "C#": 1,
    "Db": 1,
    "D": 2,
    "D#": 3,
    "Eb": 3,
    "E": 4,
    "Fb": 4,
    "E#": 5,
    "F": 5,
    "F#": 6,
    "Gb": 6,
    "G": 7,
    "G#": 8,
    "Ab": 8,
    "A": 9,
    "A#": 10,
    "Bb": 10,
    "B": 11,
    "Cb": 11,
    "B#": 0,
}

QUALITY_INTERVALS = {
    "maj": [0, 4, 7],
    "min": [0, 3, 7],
    "maj7": [0, 4, 7, 11],
    "min7": [0, 3, 7, 10],
    "7": [0, 4, 7, 10],
    "dim": [0, 3, 6],
    "aug": [0, 4, 8],
    "sus4": [0, 5, 7],
    "add9": [0, 4, 7, 2],
    "min7b5": [0, 3, 6, 10],
}

QUALITY_ALIASES = {
    "": "maj",
    "maj": "maj",
    "major": "maj",
    "M": "maj",
    "min": "min",
    "minor": "min",
    "m": "min",
    "maj7": "maj7",
    "major7": "maj7",
    "M7": "maj7",
    "min7": "min7",
    "minor7": "min7",
    "m7": "min7",
    "7": "7",
    "dim": "dim",
    "aug": "aug",
    "+": "aug",
    "sus4": "sus4",
    "add9": "add9",
    "m7b5": "min7b5",
    "min7b5": "min7b5",
}

ROOT_PATTERN = re.compile(r"^\s*([A-Ga-g])([#b]?)(.*)$")
BASS_PATTERN = re.compile(r"^\s*([A-Ga-g])([#b]?)\s*$")


@dataclass(frozen=True)
class ParsedRoot:
    root: str
    remainder: str


def normalize_chord(raw_symbol: str) -> ChordNormalizationResult:
    warnings: list[ParseWarning] = []
    parsed = _parse_root(raw_symbol)
    if parsed is None:
        return _failure(raw_symbol, "Could not parse raw chord symbol.")

    body_remainder, bass = _split_bass(parsed.remainder)
    if bass is None and "/" in parsed.remainder:
        return _failure(raw_symbol, "Could not parse slash-chord bass.")

    quality, quality_warning = _normalize_quality(body_remainder, raw_symbol)
    if quality is None:
        return _failure(raw_symbol, "Unsupported chord quality.")
    if quality_warning is not None:
        warnings.append(quality_warning)

    intervals = QUALITY_INTERVALS[quality]
    root_pc = NOTE_TO_PITCH_CLASS[parsed.root]
    pitch_classes = [(root_pc + interval) % 12 for interval in intervals]
    symbol = f"{parsed.root}:{quality}"
    if bass is not None:
        symbol = f"{symbol}/{bass}"

    chord = CanonicalChord(
        raw_symbol=raw_symbol,
        symbol=symbol,
        root=parsed.root,
        quality=quality,
        bass=bass,
        pitch_classes=pitch_classes,
        intervals=intervals,
        warnings=warnings,
    )
    return ChordNormalizationResult(
        raw_symbol=raw_symbol,
        success=True,
        chord=chord,
        warnings=warnings,
    )


def _parse_root(raw_symbol: str) -> ParsedRoot | None:
    match = ROOT_PATTERN.match(raw_symbol)
    if match is None:
        return None
    root = match.group(1).upper() + match.group(2)
    if root not in NOTE_TO_PITCH_CLASS:
        return None
    return ParsedRoot(root=root, remainder=match.group(3))


def _split_bass(remainder: str) -> tuple[str, str | None]:
    if "/" not in remainder:
        return remainder, None

    body, bass_raw = remainder.split("/", 1)
    bass_match = BASS_PATTERN.match(bass_raw)
    if bass_match is None:
        return body, None

    bass = bass_match.group(1).upper() + bass_match.group(2)
    if bass not in NOTE_TO_PITCH_CLASS:
        return body, None
    return body, bass


def _normalize_quality(
    raw_quality: str,
    raw_symbol: str,
) -> tuple[str | None, ParseWarning | None]:
    compact = re.sub(r"\s+", "", raw_quality.strip())
    quality = QUALITY_ALIASES.get(compact)
    if quality is None:
        quality = QUALITY_ALIASES.get(compact.lower())
    if quality is None:
        return None, None

    warning = None
    if compact and compact != quality:
        warning = ParseWarning(
            code="alias_normalized",
            message=f"Normalized quality alias {compact} to {quality}.",
            raw_value=raw_symbol,
        )
    return quality, warning


def _failure(raw_symbol: str, message: str) -> ChordNormalizationResult:
    warning = ParseWarning(
        code="unparseable_chord",
        message=message,
        raw_value=raw_symbol,
    )
    return ChordNormalizationResult(
        raw_symbol=raw_symbol,
        success=False,
        chord=None,
        warnings=[warning],
    )
