from collections.abc import Sequence

from app.schemas import AnalyzeProgressionResponse, ParseWarning
from app.theory.progression_normalizer import normalize_progression
from app.theory.relationships import label_progression_relationships
from app.theory.roman_analysis import analyze_progression


def analyze_progression_service(
    chords: str | Sequence[str],
    key: str | None = None,
) -> AnalyzeProgressionResponse:
    normalized = normalize_progression(chords)
    roman = analyze_progression(chords, key=key)
    relationships = label_progression_relationships(
        roman.roman_chords,
        mode_context=roman.mode,
    )

    return AnalyzeProgressionResponse(
        absolute_chords=[chord.symbol for chord in normalized.chords],
        roman_chords=roman.roman_chords,
        detected_key=roman.key,
        confidence=roman.confidence,
        warnings=_dedupe_warnings(normalized.warnings + roman.warnings),
        relationships=relationships,
    )


def _dedupe_warnings(warnings: list[ParseWarning]) -> list[ParseWarning]:
    seen = set()
    deduped = []
    for warning in warnings:
        key = (warning.code, warning.message, warning.raw_value)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(warning)
    return deduped
