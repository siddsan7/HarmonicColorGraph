import re
from collections.abc import Sequence

from app.schemas import NormalizedProgression, ParseWarning
from app.theory.chord_normalizer import normalize_chord

SEPARATOR_PATTERN = re.compile(r"\s*(?:-|,|\|)\s*")


def normalize_progression(raw_progression: str | Sequence[str]) -> NormalizedProgression:
    tokens = _tokenize_progression(raw_progression)
    chords = []
    skipped_tokens: list[str] = []
    warnings: list[ParseWarning] = []

    for token in tokens:
        result = normalize_chord(token)
        if result.chord is None:
            skipped_tokens.append(token)
            warnings.extend(result.warnings)
            continue
        chords.append(result.chord)

    total_tokens = len(tokens)
    success_rate = len(chords) / total_tokens if total_tokens else 0.0

    return NormalizedProgression(
        raw_input=raw_progression,
        chords=chords,
        skipped_tokens=skipped_tokens,
        warnings=warnings,
        success=bool(chords) and not skipped_tokens,
        chord_parse_success_rate=success_rate,
    )


def _tokenize_progression(raw_progression: str | Sequence[str]) -> list[str]:
    if isinstance(raw_progression, str):
        parts = SEPARATOR_PATTERN.split(raw_progression.strip())
        if len(parts) == 1 and " " in raw_progression.strip():
            parts = raw_progression.strip().split()
    else:
        parts = list(raw_progression)

    return [part.strip() for part in parts if part and part.strip()]

