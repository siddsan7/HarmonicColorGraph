import csv
import json
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

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


SECTION_MARKER_PATTERN = re.compile(r"<([^>]+)>")


def iter_chordonomicon_rows(
    path: str | Path,
    limit: int | None = None,
) -> Iterator[ChordonomiconSourceRow]:
    source_path = Path(path)
    yielded = 0
    iterator = (
        _iter_csv_rows(source_path)
        if source_path.suffix.lower() == ".csv"
        else _iter_jsonl_rows(source_path)
    )
    for row in iterator:
        if limit is not None and yielded >= limit:
            break
        yielded += 1
        yield row


def load_chordonomicon_sample(
    path: str | Path,
    limit: int | None = None,
) -> ChordonomiconIngestionSummary:
    rows: list[ChordonomiconSourceRow] = []
    warning_counts: Counter[str] = Counter()
    skipped_tokens: Counter[str] = Counter()
    total_tokens = 0
    parsed_tokens = 0
    rows_processed = 0
    progression_success_count = 0

    for row in iter_chordonomicon_rows(path, limit=limit):
        normalized = row.normalized_progression
        rows_processed += 1
        total_tokens += len(normalized.chords) + len(normalized.skipped_tokens)
        parsed_tokens += len(normalized.chords)
        if normalized.success:
            progression_success_count += 1
        for warning in normalized.warnings:
            warning_counts[warning.code] += 1
        for token in normalized.skipped_tokens:
            skipped_tokens[token] += 1
        rows.append(row)

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


def _iter_jsonl_rows(source_path: Path) -> Iterator[ChordonomiconSourceRow]:
    with source_path.open("r", encoding="utf-8-sig") as handle:
        for line in handle:
            if not line.strip():
                continue

            payload = json.loads(line)
            raw_chords = _extract_chords(payload)
            normalized = normalize_progression(raw_chords)
            yield _map_source_row(payload, raw_chords, normalized)


def _iter_csv_rows(source_path: Path) -> Iterator[ChordonomiconSourceRow]:
    with source_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for payload in reader:
            for section_name, raw_chords in _extract_csv_sections(payload):
                normalized = normalize_progression(raw_chords)
                yield _map_csv_source_row(
                    payload,
                    raw_chords,
                    normalized,
                    section_name,
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


def _map_csv_source_row(
    payload: dict[str, Any],
    raw_chords: str | list[str],
    normalized: NormalizedProgression,
    section: str | None,
) -> ChordonomiconSourceRow:
    return ChordonomiconSourceRow(
        source="Chordonomicon",
        source_song_id=str(payload.get("id") or ""),
        title=None,
        artist=payload.get("artist_id"),
        spotify_id=payload.get("spotify_song_id"),
        genre=_clean_csv_value(payload.get("main_genre"))
        or _clean_csv_value(payload.get("genres")),
        subgenre=_clean_csv_value(payload.get("rock_genre")),
        section=section,
        release_date=_clean_csv_value(payload.get("release_date"))
        or _clean_csv_decade(payload.get("decade")),
        key=None,
        raw_chords=raw_chords,
        normalized_progression=normalized,
    )


def _extract_csv_sections(payload: dict[str, Any]) -> Iterator[tuple[str | None, str]]:
    raw = payload.get("chords") or ""
    matches = list(SECTION_MARKER_PATTERN.finditer(raw))
    if not matches:
        cleaned = raw.strip()
        if cleaned:
            yield None, cleaned
        return

    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(raw)
        chords = raw[start:end].strip()
        if not chords:
            continue
        yield _normalize_section_name(match.group(1)), chords


def _normalize_section_name(marker: str) -> str:
    return marker.strip().split("_", 1)[0].lower()


def _clean_csv_value(value: Any) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def _clean_csv_decade(value: Any) -> str | None:
    cleaned = _clean_csv_value(value)
    if cleaned is None:
        return None
    try:
        return str(int(float(cleaned)))
    except ValueError:
        return cleaned
