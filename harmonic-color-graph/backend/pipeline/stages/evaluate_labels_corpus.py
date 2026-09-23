"""Report F13 transition-label coverage on a reproducible corpus sample."""

import argparse
from collections import defaultdict
from pathlib import Path

from app.ingestion.chordonomicon import iter_chordonomicon_rows
from app.theory.keys import estimate_song_keys
from app.theory.relationships_v2 import analyze_relationships
from app.theory.roman import romanize_chord

ROOT = Path(__file__).resolve().parents[3]


def evaluate(source: Path, song_limit: int = 20_000) -> str:
    songs: dict[str, list[list]] = defaultdict(list)
    for row in iter_chordonomicon_rows(source):
        if row.source_song_id not in songs and len(songs) >= song_limit:
            break
        if row.normalized_progression.chords:
            songs[row.source_song_id].append(row.normalized_progression.chords)

    transitions = labeled = sections_count = 0
    for sections in songs.values():
        if not sections:
            continue
        key_result = estimate_song_keys(sections)
        for chords, key in zip(sections, key_result.section_keys, strict=True):
            sections_count += 1
            if len(chords) < 2:
                continue
            tokens = [
                romanize_chord(
                    chord,
                    key,
                    previous_chord=chords[index - 1] if index else None,
                    next_chord=chords[index + 1] if index + 1 < len(chords) else None,
                    chord_index=index,
                )
                for index, chord in enumerate(chords)
            ]
            facts = analyze_relationships(tokens)
            covered = set()
            for fact in facts:
                covered.update(range(fact.from_index, fact.to_index))
            transitions += len(chords) - 1
            labeled += len(covered)
    return (
        "# Relationship Catalog Coverage (F13)\n\n"
        f"First {len(songs):,} songs, {sections_count:,} parseable sections from "
        f"`{source.name}`.\n\n"
        f"- Transitions with at least one v2 relationship: {labeled:,}/{transitions:,} "
        f"(**{labeled / transitions:.1%}**).\n"
        "- Coverage counts a trigram label for both adjacent transitions it spans.\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--songs", type=int, default=20_000)
    args = parser.parse_args()
    report = evaluate(args.source, args.songs)
    (ROOT / "docs/eval/labels.md").write_text(report, encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
