"""Measure key-confidence saturation and local modulation rate on a song sample."""

import argparse
from collections import defaultdict
from pathlib import Path

from app.ingestion.chordonomicon import iter_chordonomicon_rows
from app.theory.keys import estimate_song_keys

ROOT = Path(__file__).resolve().parents[3]


def evaluate(source: Path, song_limit: int = 20_000) -> str:
    songs: dict[str, list[list]] = defaultdict(list)
    for row in iter_chordonomicon_rows(source):
        identifier = row.source_song_id
        if identifier not in songs and len(songs) >= song_limit:
            break
        if row.normalized_progression.chords:
            songs[identifier].append(row.normalized_progression.chords)

    confidence_max_bin = 0
    sections_total = 0
    section_disagreement = 0
    song_count = 0
    for sections in songs.values():
        if not sections:
            continue
        result = estimate_song_keys(sections)
        song_count += 1
        confidence_max_bin += result.song_key_estimate.best.probability >= 0.95
        sections_total += len(sections)
        section_disagreement += sum(key != result.song_key for key in result.section_keys)

    return (
        f"\n## Full-corpus song sample\n\n"
        f"First {song_count:,} songs with parseable sections from `{source.name}`; "
        f"{sections_total:,} sections.\n\n"
        f"- Confidence in max bin (p >= 0.95): {confidence_max_bin / song_count:.1%} "
        f"({confidence_max_bin:,}/{song_count:,} songs).\n"
        f"- Section/song key disagreement: {section_disagreement / sections_total:.1%} "
        f"({section_disagreement:,}/{sections_total:,} sections).\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--songs", type=int, default=20_000)
    args = parser.parse_args()
    report = evaluate(args.source, args.songs)
    output = ROOT / "docs/eval/keys.md"
    existing = output.read_text(encoding="utf-8")
    existing = existing.split("\n## Full-corpus song sample", 1)[0].rstrip()
    output.write_text(existing + "\n" + report, encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
