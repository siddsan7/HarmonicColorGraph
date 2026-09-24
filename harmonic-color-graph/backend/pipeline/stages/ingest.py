"""F20 `ingest` stage: stream the source CSV, split into sections, dedupe
identical sections within a song (keeping a repeat count), and assign a
deterministic train/dev/test split per song.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import polars as pl

from app.ingestion.chordonomicon import ChordonomiconSourceRow, iter_chordonomicon_songs

Split = Literal["train", "dev", "test"]

INGEST_SCHEMA = {
    "song_index": pl.Int64,
    "song_id": pl.Utf8,
    "ordinal": pl.Int64,
    "section": pl.Utf8,
    "chords": pl.Utf8,
    "genre": pl.Utf8,
    "subgenre": pl.Utf8,
    "decade": pl.Utf8,
    "spotify_id": pl.Utf8,
    "split": pl.Utf8,
    "repeat_count": pl.Int64,
}


@dataclass
class IngestSummary:
    songs_processed: int = 0
    sections_total: int = 0
    sections_after_dedupe: int = 0
    split_counts: dict[str, int] = field(default_factory=lambda: {"train": 0, "dev": 0, "test": 0})

    @property
    def dedupe_rate(self) -> float:
        if self.sections_total == 0:
            return 0.0
        return 1 - (self.sections_after_dedupe / self.sections_total)


def assign_split(song_id: str) -> Split:
    """Deterministic split by `hash(source_id) % 20` (0 = test, 1 = dev,
    2-19 = train). Uses SHA-256, not Python's salted `hash()`, so the
    assignment is stable across processes and runs.
    """
    digest = hashlib.sha256(song_id.encode("utf-8")).hexdigest()
    bucket = int(digest, 16) % 20
    if bucket == 0:
        return "test"
    if bucket == 1:
        return "dev"
    return "train"


def _raw_chords_text(raw_chords: str | list[str]) -> str:
    return raw_chords if isinstance(raw_chords, str) else " ".join(raw_chords)


def _dedupe_song_sections(
    rows: list[ChordonomiconSourceRow],
) -> tuple[list[dict], int]:
    """Collapse sections with an identical chords string, keeping the first
    occurrence's position, name, and metadata, and counting repeats. Matches
    on chords content alone (not section name): a `verse` and `chorus` that
    happen to share the same four chords are still repeated material for
    aggregate/evaluation purposes (docs/roadmap-v2.md §2.3's measured 23.9%
    duplicate-section rate is by content, not by (name, chords)).
    """
    seen: dict[str, int] = {}
    sections: list[dict] = []
    for row in rows:
        chords_text = _raw_chords_text(row.raw_chords)
        signature = chords_text
        existing_index = seen.get(signature)
        if existing_index is not None:
            sections[existing_index]["repeat_count"] += 1
            continue
        seen[signature] = len(sections)
        sections.append(
            {
                "section": row.section,
                "chords": chords_text,
                "genre": row.genre,
                "subgenre": row.subgenre,
                "decade": row.release_date,
                "spotify_id": row.spotify_id,
                "repeat_count": 1,
            }
        )
    return sections, len(rows)


def run_ingest(
    source_path: str | Path,
    output_path: str | Path,
    limit: int | None = None,
    split_filter: Literal["all", "train"] = "all",
) -> IngestSummary:
    """Stream `source_path`, write the deduped, split-assigned section table
    to `output_path` (parquet), and return a summary for the manifest and
    console report.
    """
    summary = IngestSummary()
    records: list[dict] = []

    for song_index, rows in enumerate(iter_chordonomicon_songs(source_path, limit=limit)):
        song_id = rows[0].source_song_id
        split = assign_split(song_id)
        if split_filter == "train" and split != "train":
            continue
        summary.songs_processed += 1
        summary.split_counts[split] += 1

        sections, sections_total = _dedupe_song_sections(rows)
        summary.sections_total += sections_total
        summary.sections_after_dedupe += len(sections)

        for ordinal, section in enumerate(sections):
            records.append(
                {
                    "song_index": song_index,
                    "song_id": song_id,
                    "ordinal": ordinal,
                    "section": section["section"],
                    "chords": section["chords"],
                    "genre": section["genre"],
                    "subgenre": section["subgenre"],
                    "decade": section["decade"],
                    "spotify_id": section["spotify_id"],
                    "split": split,
                    "repeat_count": section["repeat_count"],
                }
            )

    frame = pl.DataFrame(records, schema=INGEST_SCHEMA)
    frame = frame.sort(["song_index", "ordinal"])
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame.write_parquet(output_path)
    return summary
