import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.schemas import NormalizedProgression
from app.theory.progression_normalizer import normalize_progression


@dataclass(frozen=True)
class ChordonomiconSourceRow:
    source: str
    source_song_id: str
    title: str | None
    artist: str | None
    spotify_id: str | None
    genre: str | None
    subgenre: str | None
    section: str | None
    release_date: str | None
    key: str | None
    raw_chords: str | list[str]
    normalized_progression: NormalizedProgression


@dataclass(frozen=True)
class ChordonomiconIngestionSummary:
    rows_processed: int
    progressions_loaded: int
    progression_success_count: int
    chord_parse_success_rate: float
    warning_counts: Counter[str] = field(default_factory=Counter)
    top_failures: list[tuple[str, int]] = field(default_factory=list)
    rows: list[ChordonomiconSourceRow] = field(default_factory=list)


def load_chordonomicon_sample(
    path: str | Path,
    limit: int | None = None,
) -> ChordonomiconIngestionSummary:
    source_path = Path(path)
    rows: list[ChordonomiconSourceRow] = []
    warning_counts: Counter[str] = Counter()
    skipped_tokens: Counter[str] = Counter()
    total_tokens = 0
    parsed_tokens = 0
    rows_processed = 0
    progression_success_count = 0

    with source_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if limit is not None and rows_processed >= limit:
                break
            if not line.strip():
                continue

            payload = json.loads(line)
            raw_chords = _extract_chords(payload)
            normalized = normalize_progression(raw_chords)
            rows_processed += 1
            total_tokens += len(normalized.chords) + len(normalized.skipped_tokens)
            parsed_tokens += len(normalized.chords)
            if normalized.success:
                progression_success_count += 1
            for warning in normalized.warnings:
                warning_counts[warning.code] += 1
            for token in normalized.skipped_tokens:
                skipped_tokens[token] += 1
            rows.append(_map_source_row(payload, raw_chords, normalized))

    chord_parse_success_rate = parsed_tokens / total_tokens if total_tokens else 0.0
    return ChordonomiconIngestionSummary(
        rows_processed=rows_processed,
        progressions_loaded=len(rows),
        progression_success_count=progression_success_count,
        chord_parse_success_rate=chord_parse_success_rate,
        warning_counts=warning_counts,
        top_failures=skipped_tokens.most_common(10),
        rows=rows,
    )


def _extract_chords(payload: dict[str, Any]) -> str | list[str]:
    for key in ("chords", "progression", "chord_progression"):
        value = payload.get(key)
        if value:
            return value
    return []


def _map_source_row(
    payload: dict[str, Any],
    raw_chords: str | list[str],
    normalized: NormalizedProgression,
) -> ChordonomiconSourceRow:
    return ChordonomiconSourceRow(
        source="Chordonomicon",
        source_song_id=str(payload.get("song_id") or payload.get("id") or ""),
        title=payload.get("title"),
        artist=payload.get("artist"),
        spotify_id=payload.get("spotify_id"),
        genre=payload.get("genre"),
        subgenre=payload.get("subgenre"),
        section=payload.get("section"),
        release_date=str(payload["release_date"])
        if payload.get("release_date") is not None
        else None,
        key=payload.get("key"),
        raw_chords=raw_chords,
        normalized_progression=normalized,
    )
