"""F20 `analyze` stage: run the v2 key finder (F11), functional Roman
analysis (F12), and relationship catalog (F13) per song, over a
multiprocessing pool, and write one row per (deduped) section.
"""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from itertools import groupby, islice
from pathlib import Path

import polars as pl

from app.theory.keys import estimate_song_keys
from app.theory.progression_normalizer import normalize_progression
from app.theory.relationships_v2 import analyze_relationships
from app.theory.roman import romanize_chord

SECTIONS_SCHEMA = {
    "song_index": pl.Int64,
    "song_id": pl.Utf8,
    "ordinal": pl.Int64,
    "section": pl.Utf8,
    "local_key": pl.Utf8,
    "source_ordinal": pl.Int64,
    "start_chord_index": pl.Int64,
    "key_conf": pl.Float64,
    "ambiguous": pl.Boolean,
    "tokens": pl.List(pl.Utf8),
    "figures": pl.List(pl.Utf8),
    "chords": pl.List(pl.Utf8),
    "labels": pl.List(pl.Utf8),
    "genre": pl.Utf8,
    "decade": pl.Utf8,
    "spotify_id": pl.Utf8,
    "split": pl.Utf8,
    "repeat_count": pl.Int64,
}


@dataclass
class AnalyzeSummary:
    songs_analyzed: int = 0
    songs_skipped_no_chords: int = 0
    sections_written: int = 0
    tokens_total: int = 0
    labels_total: int = 0
    ambiguous_songs: int = 0

    @property
    def ambiguous_rate(self) -> float:
        return self.ambiguous_songs / self.songs_analyzed if self.songs_analyzed else 0.0


def _analyze_song(song_rows: list[dict]) -> list[dict]:
    """Analyze one song's ordered, deduped sections. Runs in a worker
    process, so it takes and returns plain dicts (picklable), not the
    Pydantic models `app.theory` otherwise returns.
    """
    chords_per_section = [normalize_progression(row["chords"]).chords for row in song_rows]
    if not any(chords_per_section):
        return []

    section_names = [row["section"] or f"section_{index}" for index, row in enumerate(song_rows)]
    repeat_weights = [row["repeat_count"] for row in song_rows]
    key_result = estimate_song_keys(
        chords_per_section,
        repetition_weights=repeat_weights,
        section_names=section_names,
    )
    ambiguous = key_result.song_key_estimate.ambiguous

    output_rows: list[dict] = []
    section_tokens: list[list] = []
    offset = 0
    has_regions = any(len(regions) > 1 for regions in key_result.section_regions)
    key_boundaries: set[int] = set()
    previous_key: str | None = None
    for index, row in enumerate(song_rows):
        section_chords = chords_per_section[index]
        for region in key_result.section_regions[index]:
            if previous_key is not None and previous_key != region.key:
                key_boundaries.add(offset + region.start)
            previous_key = region.key
            tokens = [
                romanize_chord(
                    section_chords[position],
                    region.key,
                    next_chord=section_chords[position + 1] if position + 1 < region.end else None,
                    previous_chord=section_chords[position - 1]
                    if position > region.start
                    else None,
                    chord_index=offset + position,
                )
                for position in range(region.start, region.end)
            ]
            section_tokens.append(tokens)
            output_rows.append(
                {
                    "song_index": row["song_index"],
                    "song_id": row["song_id"],
                    "ordinal": len(output_rows) if has_regions else row["ordinal"],
                    "source_ordinal": row["ordinal"],
                    "start_chord_index": region.start,
                    "section": row["section"],
                    "local_key": region.key,
                    "key_conf": region.confidence,
                    "ambiguous": ambiguous,
                    "tokens": [token.core for token in tokens],
                    "figures": [token.figure for token in tokens],
                    "chords": [chord.symbol for chord in section_chords[region.start : region.end]],
                    "labels": [],
                    "genre": row["genre"],
                    "decade": row["decade"],
                    "spotify_id": row["spotify_id"],
                    "split": row["split"],
                    "repeat_count": row["repeat_count"],
                }
            )
        offset += len(section_chords)

    all_tokens = [token for tokens in section_tokens for token in tokens]
    boundaries: list[tuple[int, int]] = []
    cumulative = 0
    for tokens in section_tokens:
        boundaries.append((cumulative, cumulative + len(tokens)))
        cumulative += len(tokens)

    for fact in analyze_relationships(all_tokens, key_boundaries):
        for section_position, (start, end) in enumerate(boundaries):
            if start <= fact.from_index < end:
                output_rows[section_position]["labels"].append(fact.id)
                break

    return output_rows


DEFAULT_FLUSH_EVERY_ROWS = 100_000


def run_analyze(
    ingest_path: str | Path,
    output_path: str | Path,
    workers: int = 1,
    flush_every_rows: int = DEFAULT_FLUSH_EVERY_ROWS,
) -> AnalyzeSummary:
    """Analyze every song and stream-write `sections.parquet` in batches.

    Holding all output rows in memory before a single `write_parquet` call
    peaks around 15+ GB on the full ~2.25M-section corpus (each row carries
    several nested token/figure/chord/label lists, and Python dict/list
    overhead dwarfs the "real" data). Writing in batches via a raw
    `pyarrow.parquet.ParquetWriter` bounds peak memory to roughly one
    batch's worth of rows instead of the whole corpus. Songs are processed
    and flushed in the same (song_index, ordinal) order `ingest` wrote them
    in, so the output is already sorted without a final re-sort pass.
    """
    import pyarrow.parquet as pq

    frame = pl.read_parquet(ingest_path).sort(["song_index", "ordinal"])
    rows = (row for batch in frame.iter_slices(10_000) for row in batch.iter_rows(named=True))
    songs = (list(group) for _, group in groupby(rows, key=lambda row: row["song_index"]))

    summary = AnalyzeSummary()
    pending_rows: list[dict] = []
    writer: pq.ParquetWriter | None = None
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    def flush() -> None:
        nonlocal writer, pending_rows
        if not pending_rows:
            return
        table = pl.DataFrame(pending_rows, schema=SECTIONS_SCHEMA).to_arrow()
        if writer is None:
            writer = pq.ParquetWriter(str(output_path), table.schema)
        writer.write_table(table)
        pending_rows = []

    try:
        if workers > 1:
            with ProcessPoolExecutor(max_workers=workers) as pool:
                # Executor.map eagerly submits its iterable on Python 3.12.
                # Bound submitted input/results instead of materializing the
                # full corpus as millions of Python dictionaries and futures.
                while batch := list(islice(songs, 256)):
                    for result_rows in pool.map(_analyze_song, batch, chunksize=32):
                        _fold_song_result(result_rows, summary, pending_rows)
                        if len(pending_rows) >= flush_every_rows:
                            flush()
        else:
            for song_rows in songs:
                _fold_song_result(_analyze_song(song_rows), summary, pending_rows)
                if len(pending_rows) >= flush_every_rows:
                    flush()
        flush()
    finally:
        if writer is not None:
            writer.close()

    if writer is None:
        pl.DataFrame([], schema=SECTIONS_SCHEMA).write_parquet(output_path)

    return summary


def _fold_song_result(
    result_rows: list[dict],
    summary: AnalyzeSummary,
    pending_rows: list[dict],
) -> None:
    if not result_rows:
        summary.songs_skipped_no_chords += 1
        return
    summary.songs_analyzed += 1
    summary.sections_written += len(result_rows)
    summary.tokens_total += sum(len(row["tokens"]) for row in result_rows)
    summary.labels_total += sum(len(row["labels"]) for row in result_rows)
    if result_rows[0]["ambiguous"]:
        summary.ambiguous_songs += 1
    pending_rows.extend(result_rows)
