"""F21: quality report over a completed `analyze` run's `sections.parquet`
-- token parse rate, key confidence histogram, ambiguity/modulation share,
top core tokens, label coverage, and a random sample of songs rendered as
`chords -> figures` for a musician spot-check.
"""

from __future__ import annotations

import random
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

# sections.parquet stores CanonicalChord.symbol ("C:maj", "F:min7/A", ...),
# the canonical root:quality[/bass] form used across the app. Musicians
# spot-checking the sample read conventional notation instead.
QUALITY_DISPLAY = {
    "maj": "",
    "min": "m",
    "dim": "dim",
    "aug": "aug",
    "dom7": "7",
    "maj7": "maj7",
    "min7": "m7",
    "hdim7": "m7b5",
    "dim7": "dim7",
    "minmaj7": "mMaj7",
    "sus": "sus",
    "power": "5",
}


def _display_chord(symbol: str) -> str:
    body, _, bass = symbol.partition("/")
    root, _, quality = body.partition(":")
    display = root + QUALITY_DISPLAY.get(quality, quality)
    return f"{display}/{bass}" if bass else display


CONFIDENCE_BUCKETS = [
    ("< 0.50", 0.0, 0.50),
    ("0.50-0.70", 0.50, 0.70),
    ("0.70-0.85", 0.70, 0.85),
    ("0.85-0.95", 0.85, 0.95),
    (">= 0.95", 0.95, 1.0 + 1e-9),
]


@dataclass
class SampleSection:
    section: str | None
    local_key: str
    chords: list[str]
    figures: list[str]


@dataclass
class SampleSong:
    song_id: str
    genre: str | None
    decade: str | None
    sections: list[SampleSection]


@dataclass
class CorpusReport:
    version: str
    songs: int
    sections: int
    tokens: int
    key_conf_histogram: dict[str, int] = field(default_factory=dict)
    ambiguous_song_rate: float = 0.0
    modulation_song_rate: float = 0.0
    top_core_tokens: list[tuple[str, int]] = field(default_factory=list)
    label_coverage_rate: float = 0.0
    sample_songs: list[SampleSong] = field(default_factory=list)
    external_parse_rate: float | None = None
    external_parse_rate_source: str | None = None


def build_corpus_report(
    sections_path: str | Path,
    version: str,
    sample_seed: int = 1,
    sample_size: int = 20,
    top_n: int = 50,
    external_parse_rate: float | None = None,
    external_parse_rate_source: str | None = None,
) -> CorpusReport:
    import polars as pl

    frame = pl.read_parquet(sections_path)
    songs_frame = frame.group_by("song_id").agg(
        pl.col("ambiguous").first().alias("ambiguous"),
        pl.col("local_key").n_unique().alias("distinct_local_keys"),
        pl.col("genre").first().alias("genre"),
        pl.col("decade").first().alias("decade"),
    )

    songs = songs_frame.height
    sections = frame.height
    tokens = int(frame["tokens"].list.len().sum())

    histogram = {label: 0 for label, _, _ in CONFIDENCE_BUCKETS}
    for value in frame["key_conf"]:
        for label, low, high in CONFIDENCE_BUCKETS:
            if low <= value < high:
                histogram[label] += 1
                break

    ambiguous_song_rate = float(songs_frame["ambiguous"].sum()) / songs if songs else 0.0
    modulation_song_rate = (
        float((songs_frame["distinct_local_keys"] > 1).sum()) / songs if songs else 0.0
    )

    token_counts: Counter[str] = Counter()
    for row_tokens in frame["tokens"]:
        token_counts.update(row_tokens)
    top_core_tokens = token_counts.most_common(top_n)

    labelled_sections = int((frame["labels"].list.len() > 0).sum())
    label_coverage_rate = labelled_sections / sections if sections else 0.0

    rng = random.Random(sample_seed)
    song_ids = songs_frame["song_id"].to_list()
    sample_ids = set(rng.sample(song_ids, min(sample_size, len(song_ids))))
    sample_songs = _render_sample_songs(frame, sample_ids)

    return CorpusReport(
        version=version,
        songs=songs,
        sections=sections,
        tokens=tokens,
        key_conf_histogram=histogram,
        ambiguous_song_rate=ambiguous_song_rate,
        modulation_song_rate=modulation_song_rate,
        top_core_tokens=top_core_tokens,
        label_coverage_rate=label_coverage_rate,
        sample_songs=sample_songs,
        external_parse_rate=external_parse_rate,
        external_parse_rate_source=external_parse_rate_source,
    )


def _render_sample_songs(frame, sample_ids: set[str]) -> list[SampleSong]:
    subset = frame.filter(frame["song_id"].is_in(list(sample_ids))).sort(["song_id", "ordinal"])
    songs: dict[str, SampleSong] = {}
    for row in subset.to_dicts():
        song = songs.get(row["song_id"])
        if song is None:
            song = SampleSong(
                song_id=row["song_id"], genre=row["genre"], decade=row["decade"], sections=[]
            )
            songs[row["song_id"]] = song
        song.sections.append(
            SampleSection(
                section=row["section"],
                local_key=row["local_key"],
                chords=row["chords"],
                figures=row["figures"],
            )
        )
    # Preserve the deterministic sample order, not parquet filter order.
    return [songs[song_id] for song_id in sample_ids if song_id in songs]


def render_corpus_report_markdown(report: CorpusReport) -> str:
    lines = [f"# Corpus Analysis Report -- `{report.version}`", ""]
    lines.append(f"- Songs analyzed: {report.songs:,}")
    lines.append(f"- Sections analyzed: {report.sections:,}")
    lines.append(f"- Tokens analyzed: {report.tokens:,}")
    if report.external_parse_rate is not None:
        lines.append(
            f"- Token parse rate: **{report.external_parse_rate:.4%}** "
            f"(from {report.external_parse_rate_source}; chord-parsing logic is "
            "unchanged since that report, so it applies to this run too)"
        )
    lines.append(f"- Ambiguous-key songs: **{report.ambiguous_song_rate:.1%}**")
    lines.append(f"- Songs with a detected modulation: **{report.modulation_song_rate:.1%}**")
    lines.append(
        f"- Label coverage (sections with >= 1 relationship fact): "
        f"**{report.label_coverage_rate:.1%}**"
    )
    lines.append("")

    lines.append("## Key confidence histogram (per section)")
    lines.append("")
    lines.append("| Bucket | Sections | Share |")
    lines.append("| --- | ---: | ---: |")
    for label, count in report.key_conf_histogram.items():
        share = count / report.sections if report.sections else 0.0
        lines.append(f"| {label} | {count:,} | {share:.1%} |")
    lines.append("")

    lines.append(f"## Top {len(report.top_core_tokens)} core tokens")
    lines.append("")
    lines.append("| Core token | Count |")
    lines.append("| --- | ---: |")
    for token, count in report.top_core_tokens:
        lines.append(f"| `{token}` | {count:,} |")
    lines.append("")

    lines.append(f"## Spot-check sample ({len(report.sample_songs)} songs)")
    lines.append("")
    lines.append(
        "Deterministic random sample for a musician spot-check "
        "(>= 18/20 should look musically right; otherwise F11/F12 need another pass)."
    )
    lines.append("")
    for song in report.sample_songs:
        genre = song.genre or "unknown genre"
        decade = song.decade or "unknown decade"
        lines.append(f"### Song `{song.song_id}` ({genre}, {decade})")
        lines.append("")
        for section in song.sections:
            name = section.section or "(unnamed)"
            lines.append(f"- **{name}** ({section.local_key}):")
            lines.append(f"  - chords: `{' '.join(_display_chord(c) for c in section.chords)}`")
            lines.append(f"  - figures: `{' '.join(section.figures)}`")
        lines.append("")

    return "\n".join(lines) + "\n"
