"""F20 `synth`: a deterministic, no-dataset-content stand-in for the real
Chordonomicon corpus (`data/samples/mini_corpus.csv`), in the same CSV
format as `data/raw/chordonomicon_v2.csv`. Contains no dataset content, so
it is safe to commit; it feeds CI, preview environments, and F24's loader
smoke test.
"""

from __future__ import annotations

import csv
import random
from pathlib import Path

from app.theory.spelling import diatonic_letters_and_pitch_classes, spell

SEED = 20260923
SONG_COUNT = 500

KEYS = [
    f"{root} {mode}"
    for root in ("C", "G", "D", "A", "E", "B", "F", "Bb", "Eb", "Ab", "F#")
    for mode in ("major", "minor")
]

# (scale-degree index 0-6, quality suffix) pairs, spelled diatonically in
# whatever key is chosen per song. Musical "correctness" doesn't matter here
# (that is theory/roman.py's job) -- only that every symbol parses and the
# corpus profile (genres, sections, repeats) looks like the real one.
MAJOR_TEMPLATES: list[list[tuple[int, str]]] = [
    [(0, ""), (4, ""), (5, "m"), (3, "")],
    [(0, ""), (5, "m"), (3, ""), (4, "")],
    [(1, "m"), (4, ""), (0, "")],
    [(0, ""), (3, ""), (4, ""), (3, "")],
    [(5, "m"), (3, ""), (0, ""), (4, "")],
    [(0, ""), (4, ""), (5, "m"), (2, "m"), (3, ""), (0, ""), (3, ""), (4, "")],
    [(0, "maj7"), (3, "maj7"), (4, "7"), (0, "maj7")],
    [(1, "m7"), (4, "7"), (0, "maj7")],
]
MINOR_TEMPLATES: list[list[tuple[int, str]]] = [
    [(0, "m"), (5, ""), (2, ""), (6, "")],
    [(0, "m"), (3, "m"), (4, "m"), (0, "m")],
    [(0, "m"), (6, ""), (5, ""), (4, "")],
    [(0, "m"), (3, "m"), (6, ""), (2, "")],
    [(0, "m7"), (3, "m7"), (6, "7"), (2, "maj7")],
]

REPEATABLE_SECTIONS = ("verse", "chorus")
FILLER_SECTIONS = ("verse", "chorus", "bridge", "solo")
GENRES = (
    "pop",
    "rock",
    "country",
    "metal",
    "jazz",
    "folk",
    "electronic",
    "r&b",
    "hip hop",
    "indie",
)
DECADES = ("1970.0", "1980.0", "1990.0", "2000.0", "2010.0", "2020.0")

CSV_FIELDS = [
    "id",
    "chords",
    "release_date",
    "genres",
    "decade",
    "rock_genre",
    "artist_id",
    "main_genre",
    "spotify_song_id",
    "spotify_artist_id",
]


def _template_to_chords(template: list[tuple[int, str]], key: str) -> list[str]:
    degrees = diatonic_letters_and_pitch_classes(key)
    return [
        spell(pc, letter) + quality
        for degree, quality in template
        for letter, pc in (degrees[degree],)
    ]


def _build_song(rng: random.Random, song_id: int) -> dict[str, str]:
    key = rng.choice(KEYS)
    mode = key.split()[1]
    templates = MAJOR_TEMPLATES if mode == "major" else MINOR_TEMPLATES

    section_count = rng.randint(3, 6)
    plan = ["intro"] + [rng.choice(FILLER_SECTIONS) for _ in range(section_count - 2)] + ["outro"]

    section_chords: dict[str, list[str]] = {}
    name_counts: dict[str, int] = {}
    parts: list[str] = []
    for name in plan:
        reuse = name in REPEATABLE_SECTIONS and name in section_chords and rng.random() < 0.6
        if reuse:
            chords = section_chords[name]
        else:
            chords = _template_to_chords(rng.choice(templates), key)
            section_chords[name] = chords
        name_counts[name] = name_counts.get(name, 0) + 1
        parts.append(f"<{name}_{name_counts[name]}> " + " ".join(chords))
    chords_field = " ".join(parts)

    genre = rng.choice(GENRES) if rng.random() < 0.52 else ""
    decade = rng.choice(DECADES) if rng.random() < 0.62 else ""
    has_spotify = rng.random() < 0.648

    return {
        "id": str(song_id),
        "chords": chords_field,
        "release_date": "",
        "genres": f"'{genre}'" if genre else "",
        "decade": decade,
        "rock_genre": "",
        "artist_id": f"artist_{song_id}",
        "main_genre": genre,
        "spotify_song_id": f"synth{song_id:06d}" if has_spotify else "",
        "spotify_artist_id": f"synthartist{song_id:06d}" if has_spotify else "",
    }


def build_mini_corpus(song_count: int = SONG_COUNT, seed: int = SEED) -> list[dict[str, str]]:
    rng = random.Random(seed)
    return [_build_song(rng, song_id) for song_id in range(1, song_count + 1)]


def write_mini_corpus(
    output_path: str | Path, song_count: int = SONG_COUNT, seed: int = SEED
) -> Path:
    rows = build_mini_corpus(song_count, seed)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return output_path


if __name__ == "__main__":
    REPO_ROOT = Path(__file__).resolve().parents[2]
    written = write_mini_corpus(REPO_ROOT / "data" / "samples" / "mini_corpus.csv")
    print(f"Wrote {written}")
