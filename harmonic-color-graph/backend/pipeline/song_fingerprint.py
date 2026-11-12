"""Offline prototype: song-level harmonic fingerprints and a similar-song search.

Everything else in the corpus pipeline scores a chord, a transition or a short
pattern. This module aggregates the same deterministic analysis up to a whole
song so two songs can be compared by harmonic color instead of only by genre
or tempo. It is evaluation tooling only: nothing here is imported by the API,
loaded into the database or part of `hcg-build`.

A fingerprint holds, per song:

* `raw_*`   -- mean of F41's nine measurable color axes over every chord
              position (weighted by how often the section repeats).
* `perc_*`  -- mean of F42's six perceptual axes over sliding four-chord
              windows, so a long section yields a graded amount rather than
              the saturated value a single whole-section call would give.
* `arc_*`   -- chorus mean minus verse mean for the perceptual axes plus
              brightness and tension (null when the song lacks either part).
* `embed`   -- frequency-weighted mean of chord2vec function vectors.
* `bigrams` -- Roman-token transition counts, for progression overlap.
* key, mode and Camelot code for harmonic mixing.

The perceptual axes are hand-weighted formulas with no listener validation.
A fingerprint describes harmonic color; it is not a measured emotion.

    python -m pipeline.song_fingerprint build --songs 5000
    python -m pipeline.song_fingerprint proxy
    python -m pipeline.song_fingerprint sheet
    python -m pipeline.song_fingerprint similar --song-id 123
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import time
from collections import Counter, defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from app.color.features import AXES, compute_chord_color
from app.color.perceptual import PERCEPTUAL_AXES, _perceptual_from_raws
from app.theory.roman import analyze_v2

SEED = 20261111
WINDOW = 4
WINDOW_STRIDE = 2
MIN_TOKENS = 24
MIN_LABELLED_SECTIONS = 2
ARC_AXES: tuple[str, ...] = (*PERCEPTUAL_AXES, "brightness", "tension")
COMPONENTS: tuple[str, ...] = ("color", "embed", "pattern", "arc")
DEFAULT_WEIGHTS = {"color": 0.4, "embed": 0.3, "pattern": 0.3, "arc": 0.0}

_ARTIFACTS = Path(__file__).resolve().parents[2] / "data" / "artifacts"
DEFAULT_SECTIONS = _ARTIFACTS / "eval-train-a" / "sections.parquet"
DEFAULT_NGRAMS = _ARTIFACTS / "eval-train-a" / "ngrams.parquet"
DEFAULT_RAW = Path(__file__).resolve().parents[2] / "data" / "raw" / "chordonomicon_v2.csv"
DEFAULT_OUT = _ARTIFACTS / "song-fp-proto"

_PITCH_CLASS = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def camelot(key: str) -> str:
    """`"A minor"` -> `"8A"`, `"C major"` -> `"8B"` (the DJ key wheel)."""
    tonic, mode = key.split()
    pitch_class = _PITCH_CLASS[tonic[0].upper()]
    pitch_class += tonic.count("#") + tonic.count("s") - tonic[1:].count("b")
    if mode == "minor":
        pitch_class += 3  # relative major shares the wheel position
    return f"{(7 * pitch_class + 7) % 12 + 1}{'A' if mode == 'minor' else 'B'}"


def _stable_rank(value: str) -> int:
    return int.from_bytes(hashlib.blake2b(value.encode(), digest_size=8).digest(), "little")


def _mean(total: float, weight: float) -> float | None:
    return total / weight if weight else None


@dataclass
class _Accumulator:
    """Weighted running means for one group of chord positions."""

    raw_sum: dict[str, float]
    raw_weight: dict[str, float]
    perc_sum: dict[str, float]
    perc_weight: float = 0.0

    @classmethod
    def empty(cls) -> _Accumulator:
        return cls(
            raw_sum=dict.fromkeys(AXES, 0.0),
            raw_weight=dict.fromkeys(AXES, 0.0),
            perc_sum=dict.fromkeys(PERCEPTUAL_AXES, 0.0),
        )

    def raw(self, axis: str) -> float | None:
        return _mean(self.raw_sum[axis], self.raw_weight[axis])

    def perc(self, axis: str) -> float | None:
        return _mean(self.perc_sum[axis], self.perc_weight)

    def axis(self, axis: str) -> float | None:
        return self.perc(axis) if axis in PERCEPTUAL_AXES else self.raw(axis)


def fingerprint_song(sections: Sequence[dict], predictor=None) -> dict | None:
    """Fingerprint one song from its `sections.parquet` rows.

    Returns `None` when no section could be analyzed. `predictor` is the same
    optional n-gram predictor the `color` stage uses; without it `surprise`
    stays null and `resolution` falls back to cadence strength alone.
    """
    whole = _Accumulator.empty()
    parts = {"verse": _Accumulator.empty(), "chorus": _Accumulator.empty()}
    key_weight: Counter[str] = Counter()
    key_conf_sum = 0.0
    token_counts: Counter[str] = Counter()
    bigrams: Counter[str] = Counter()
    positions = 0

    for row in sorted(sections, key=lambda item: item["ordinal"]):
        chords, key = row["chords"], row["local_key"]
        if not chords or not key:
            continue
        try:
            analysis = analyze_v2([label.replace(":", "", 1) for label in chords], key)
        except ValueError:
            continue
        repeat = float(row.get("repeat_count") or 1)
        tokens = analysis.tokens
        raws = []
        history: list[str] = []
        for index, (chord, token) in enumerate(zip(analysis.chords, tokens, strict=True)):
            raws.append(
                compute_chord_color(
                    chord,
                    token,
                    key,
                    previous_chord=analysis.chords[index - 1] if index else None,
                    previous_token=tokens[index - 1] if index else None,
                    predictor=predictor,
                    history=tuple(history),
                    genre=row.get("genre"),
                    section=row.get("section"),
                )
            )
            history.append(token.core)

        targets = [whole]
        if row.get("section") in parts:
            targets.append(parts[row["section"]])
        for raw in raws:
            for axis in AXES:
                value = getattr(raw, axis)
                if value is None:
                    continue
                for target in targets:
                    target.raw_sum[axis] += value * repeat
                    target.raw_weight[axis] += repeat
        if len(tokens) >= 2:
            starts = range(0, max(len(tokens) - WINDOW, 0) + 1, WINDOW_STRIDE)
            for start in starts:
                window = slice(start, start + WINDOW)
                perceptual = _perceptual_from_raws(raws[window], tokens[window])
                for target in targets:
                    for axis in PERCEPTUAL_AXES:
                        target.perc_sum[axis] += perceptual[axis].value * repeat
                    target.perc_weight += repeat

        cores = [token.core for token in tokens]
        for core in cores:
            token_counts[core] += int(repeat)
        for left, right in zip(cores, cores[1:], strict=False):
            if left != right:
                bigrams[f"{left}>{right}"] += int(repeat)
        key_weight[key] += len(cores) * repeat
        key_conf_sum += float(row.get("key_conf") or 0.0) * len(cores) * repeat
        positions += len(cores)

    if not positions:
        return None
    key = min(key_weight, key=lambda item: (-key_weight[item], item))
    total_weight = sum(key_weight.values())
    result: dict = {
        "key": key,
        "mode": key.split()[1],
        "camelot": camelot(key),
        "key_share": key_weight[key] / total_weight,
        "key_conf": key_conf_sum / total_weight,
        "n_positions": positions,
        "token_counts": json.dumps(dict(sorted(token_counts.items()))),
        "bigrams": json.dumps(dict(sorted(bigrams.items()))),
    }
    for axis in AXES:
        result[f"raw_{axis}"] = whole.raw(axis)
    for axis in PERCEPTUAL_AXES:
        result[f"perc_{axis}"] = whole.perc(axis)
    for axis in ARC_AXES:
        verse, chorus = parts["verse"].axis(axis), parts["chorus"].axis(axis)
        result[f"arc_{axis}"] = None if verse is None or chorus is None else chorus - verse
    return result


def song_embedding(
    token_counts: dict[str, int], vectors: dict[str, np.ndarray], frequency: dict[str, float]
) -> np.ndarray | None:
    """Frequency-weighted mean of function vectors (rarer chords count more),
    the same weighting `stages/embeddings.py` uses for pattern vectors."""
    known = [token for token in sorted(token_counts) if token in vectors]
    if not known:
        return None
    weights = np.array(
        [token_counts[token] * 0.001 / (0.001 + frequency[token]) for token in known]
    )
    mean = np.average(np.stack([vectors[token] for token in known]), axis=0, weights=weights)
    norm = float(np.linalg.norm(mean))
    return (mean / norm).astype(np.float32) if norm else None


# --------------------------------------------------------------------------
# build
# --------------------------------------------------------------------------


def select_songs(sections_path: Path, songs: int) -> list[str]:
    """Deterministic sample of songs that have a Spotify ID, enough chords and
    at least two labelled sections. One song per Spotify ID."""
    import polars as pl

    eligible = (
        pl.scan_parquet(sections_path)
        .filter(pl.col("spotify_id").is_not_null() & (pl.col("spotify_id") != ""))
        .group_by("song_id")
        .agg(
            pl.col("spotify_id").first(),
            pl.col("song_index").first(),
            pl.col("tokens").list.len().sum().alias("n_tokens"),
            pl.col("section").is_not_null().sum().alias("n_labelled"),
        )
        .filter(
            (pl.col("n_tokens") >= MIN_TOKENS) & (pl.col("n_labelled") >= MIN_LABELLED_SECTIONS)
        )
        .sort("song_index")
        .unique(subset="spotify_id", keep="first", maintain_order=True)
        .collect()
    )
    ids = sorted(eligible["song_id"].to_list(), key=_stable_rank)
    return ids[:songs]


def train_function_vectors(
    sections_path: Path, max_sections: int
) -> tuple[dict[str, np.ndarray], dict[str, float]]:
    """chord2vec with the `embeddings` stage's settings, on a bounded prefix of
    train sections so the prototype does not need a full corpus rebuild."""
    from gensim.models import Word2Vec

    from pipeline.stages import embeddings as stage

    sentences = []
    for tokens in stage.TrainSentences(sections_path):
        sentences.append(tokens)
        if len(sentences) >= max_sections:
            break
    model = Word2Vec(
        sentences=sentences,
        vector_size=stage.DIM,
        window=stage.WINDOW,
        min_count=stage.MIN_COUNT,
        sg=1,
        seed=stage.SEED,
        workers=1,
        epochs=5,
        sorted_vocab=1,
        hashfxn=stage._stable_hash,
    )
    vectors = {token: stage._normalize(model.wv[token]) for token in model.wv.index_to_key}
    total = sum(model.wv.get_vecattr(token, "count") for token in vectors)
    frequency = {token: model.wv.get_vecattr(token, "count") / total for token in vectors}
    return vectors, frequency


_WORKER_PREDICTOR = None


def _init_worker(ngrams_path: str | None) -> None:
    global _WORKER_PREDICTOR
    if ngrams_path:
        from app.predict.ngram import InMemoryNgramStore, KNPredictor

        _WORKER_PREDICTOR = KNPredictor(store=InMemoryNgramStore.from_parquet(ngrams_path))


def _fingerprint_task(item: tuple[str, list[dict]]) -> tuple[str, dict | None]:
    song_id, sections = item
    return song_id, fingerprint_song(sections, _WORKER_PREDICTOR)


def _song_metadata(raw_path: Path, wanted: set[str]) -> dict[str, dict]:
    """Artist and genre tags from the source CSV, used only by the proxy check."""
    csv.field_size_limit(10**9)
    meta: dict[str, dict] = {}
    if not raw_path.is_file():
        return meta
    with raw_path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["id"] in wanted:
                tags = [tag for tag in row["genres"].split("'") if tag.strip()]
                meta[row["id"]] = {
                    "artist_id": row["artist_id"] or None,
                    "main_genre": row["main_genre"] or None,
                    "genre_tags": json.dumps(sorted(set(tags))),
                }
    return meta


def run_build(args: argparse.Namespace) -> None:
    import multiprocessing

    import polars as pl

    started = time.perf_counter()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    song_ids = select_songs(Path(args.sections), args.songs)
    wanted = set(song_ids)
    frame = (
        pl.scan_parquet(args.sections)
        .filter(pl.col("song_id").is_in(song_ids))
        .select(
            "song_id",
            "ordinal",
            "section",
            "local_key",
            "key_conf",
            "chords",
            "genre",
            "decade",
            "spotify_id",
            "repeat_count",
        )
        .collect()
    )
    by_song: dict[str, list[dict]] = defaultdict(list)
    for row in frame.iter_rows(named=True):
        by_song[row["song_id"]].append(row)
    print(f"selected {len(by_song)} songs, {frame.height} sections")

    use_predictor = not args.no_predictor and Path(args.ngrams).is_file()
    ngrams_arg = str(args.ngrams) if use_predictor else None
    items = [(song_id, by_song[song_id]) for song_id in song_ids if song_id in by_song]
    if args.workers > 1:
        with multiprocessing.Pool(args.workers, _init_worker, (ngrams_arg,)) as pool:
            results = pool.map(_fingerprint_task, items, chunksize=16)
    else:
        _init_worker(ngrams_arg)
        results = [_fingerprint_task(item) for item in items]
    print(f"fingerprinted in {time.perf_counter() - started:.0f}s")

    vectors, frequency = train_function_vectors(Path(args.sections), args.embed_sections)
    meta = _song_metadata(Path(args.raw), wanted)
    rows = []
    skipped = 0
    for song_id, fingerprint in results:
        if fingerprint is None:
            skipped += 1
            continue
        embedding = song_embedding(json.loads(fingerprint["token_counts"]), vectors, frequency)
        if embedding is None:
            skipped += 1
            continue
        first = by_song[song_id][0]
        rows.append(
            {
                "song_id": song_id,
                "spotify_id": first["spotify_id"],
                "genre": first["genre"],
                "decade": first["decade"],
                **meta.get(song_id, {"artist_id": None, "main_genre": None, "genre_tags": "[]"}),
                **fingerprint,
                "embed": embedding.tolist(),
            }
        )
    pl.DataFrame(rows, infer_schema_length=None).write_parquet(out / "fingerprints.parquet")
    summary = {
        "songs_written": len(rows),
        "songs_skipped": skipped,
        "used_predictor": use_predictor,
        "embedding_vocab": len(vectors),
        "embedding_sections": args.embed_sections,
        "seconds": round(time.perf_counter() - started, 1),
        "sections_source": str(args.sections),
    }
    (out / "build_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


# --------------------------------------------------------------------------
# similarity
# --------------------------------------------------------------------------


def _zscore_columns(matrix: np.ndarray) -> np.ndarray:
    """Column z-scores; missing values become 0 (the column mean)."""
    present = ~np.isnan(matrix)
    count = np.maximum(present.sum(axis=0), 1)
    filled = np.where(present, matrix, 0.0)
    mean = filled.sum(axis=0) / count
    std = np.sqrt((np.where(present, matrix - mean, 0.0) ** 2).sum(axis=0) / count)
    std[std == 0] = 1.0
    scored = (matrix - mean) / std
    return np.nan_to_num(scored, nan=0.0).astype(np.float32)


class SongIndex:
    """In-memory similarity over a set of fingerprint rows."""

    def __init__(self, rows: Sequence[dict]):
        from scipy import sparse
        from sklearn.feature_extraction.text import TfidfTransformer
        from sklearn.preprocessing import normalize

        self.rows = list(rows)
        self.position = {row["song_id"]: index for index, row in enumerate(self.rows)}
        color_columns = [f"raw_{axis}" for axis in AXES] + [f"perc_{a}" for a in PERCEPTUAL_AXES]
        self.color_columns = color_columns
        self.color = _zscore_columns(self._matrix(color_columns))
        arc = self._matrix([f"arc_{axis}" for axis in ARC_AXES])
        self.has_arc = ~np.isnan(arc).any(axis=1)
        self.arc = _zscore_columns(arc)
        self.embed = np.asarray([row["embed"] for row in self.rows], dtype=np.float32)

        vocabulary: dict[str, int] = {}
        indices, counts, pointers = [], [], [0]
        for row in self.rows:
            for bigram, count in json.loads(row["bigrams"]).items():
                indices.append(vocabulary.setdefault(bigram, len(vocabulary)))
                counts.append(count)
            pointers.append(len(indices))
        matrix = sparse.csr_matrix(
            (counts, indices, pointers), shape=(len(self.rows), max(len(vocabulary), 1))
        )
        self.pattern = normalize(TfidfTransformer(sublinear_tf=True).fit_transform(matrix))

    def _matrix(self, columns: Sequence[str]) -> np.ndarray:
        return np.asarray(
            [[np.nan if row[c] is None else row[c] for c in columns] for row in self.rows],
            dtype=np.float64,
        )

    def component_scores(self, queries: Sequence[int]) -> dict[str, np.ndarray]:
        """Raw similarity of each query row to every song, per component."""
        index = np.asarray(queries)
        color_distance = np.sqrt(
            np.maximum(
                (self.color[index] ** 2).sum(1)[:, None]
                + (self.color**2).sum(1)[None, :]
                - 2 * self.color[index] @ self.color.T,
                0.0,
            )
        )
        arc_distance = np.sqrt(
            np.maximum(
                (self.arc[index] ** 2).sum(1)[:, None]
                + (self.arc**2).sum(1)[None, :]
                - 2 * self.arc[index] @ self.arc.T,
                0.0,
            )
        )
        return {
            "color": -color_distance,
            "embed": self.embed[index] @ self.embed.T,
            "pattern": np.asarray((self.pattern[index] @ self.pattern.T).todense()),
            "arc": -arc_distance,
        }

    def blended(self, queries: Sequence[int], weights: dict[str, float]) -> np.ndarray:
        """Weighted sum of per-query standardized component scores, so no
        component dominates just because its numbers are larger. The arc
        component is ignored for a query or candidate without verse+chorus."""
        scores = self.component_scores(queries)
        total = np.zeros((len(queries), len(self.rows)), dtype=np.float64)
        for name, weight in weights.items():
            if not weight:
                continue
            part = scores[name]
            part = (part - part.mean(1, keepdims=True)) / (part.std(1, keepdims=True) + 1e-9)
            if name == "arc":
                part = np.where(self.has_arc[None, :], part, 0.0)
                part[~self.has_arc[np.asarray(queries)]] = 0.0
            total += weight * part
        return total

    def neighbours(
        self,
        song_id: str,
        *,
        k: int = 10,
        weights: dict[str, float] | None = None,
        exclude_same_artist: bool = True,
        camelot_compatible: bool = False,
    ) -> list[dict]:
        query = self.position[song_id]
        scores = self.blended([query], weights or DEFAULT_WEIGHTS)[0]
        source = self.rows[query]
        allowed = compatible_camelot(source["camelot"]) if camelot_compatible else None
        results = []
        for index in np.argsort(-scores, kind="stable"):
            row = self.rows[index]
            if index == query:
                continue
            if (
                exclude_same_artist
                and source["artist_id"]
                and row["artist_id"] == source["artist_id"]
            ):
                continue
            if allowed is not None and row["camelot"] not in allowed:
                continue
            results.append({**row, "score": float(scores[index])})
            if len(results) >= k:
                break
        return results


def compatible_camelot(code: str) -> set[str]:
    """Same key, relative major/minor, and one step either way on the wheel."""
    number, letter = int(code[:-1]), code[-1]
    return {
        code,
        f"{number}{'A' if letter == 'B' else 'B'}",
        f"{number % 12 + 1}{letter}",
        f"{(number - 2) % 12 + 1}{letter}",
    }


def load_index(out: Path) -> SongIndex:
    import polars as pl

    return SongIndex(pl.read_parquet(out / "fingerprints.parquet").to_dicts())


# --------------------------------------------------------------------------
# proxy check
# --------------------------------------------------------------------------


def _top_k(scores: np.ndarray, banned: np.ndarray, k: int) -> np.ndarray:
    masked = np.where(banned, -np.inf, scores)
    return np.argsort(-masked, kind="stable")[:k]


def proxy_metrics(index: SongIndex, *, queries: int, k: int, seed: int = SEED) -> dict:
    """Do nearest neighbours share metadata more often than random songs do?

    Neighbours by the same artist are excluded from the genre and decade
    measures so an artist's own catalogue cannot inflate them. This is a
    sanity proxy: genre agreement is not evidence that two songs feel alike.
    """
    rng = random.Random(seed)
    count = len(index.rows)
    chosen = sorted(rng.sample(range(count), k=min(queries, count)))
    artists = np.asarray([row["artist_id"] or f"?{i}" for i, row in enumerate(index.rows)])
    genres = [row["main_genre"] for row in index.rows]
    decades = [row["decade"] for row in index.rows]
    tags = [set(json.loads(row["genre_tags"])) for row in index.rows]
    modes = [row["mode"] for row in index.rows]

    component = index.component_scores(chosen)
    arms: dict[str, np.ndarray] = {name: component[name] for name in COMPONENTS}
    arms["blend"] = index.blended(chosen, DEFAULT_WEIGHTS)
    arms["random"] = np.random.default_rng(seed).random((len(chosen), count))

    report: dict[str, dict] = {}
    for name, scores in arms.items():
        totals: dict[str, list[float]] = defaultdict(list)
        for row_index, query in enumerate(chosen):
            if name == "arc" and not index.has_arc[query]:
                continue
            row_scores = scores[row_index]
            if name == "arc":
                row_scores = np.where(index.has_arc, row_scores, -np.inf)
            self_mask = np.arange(count) == query
            with_artist = _top_k(row_scores, self_mask, k)
            totals["same_artist"].append(float(np.mean(artists[with_artist] == artists[query])))
            picked = _top_k(row_scores, self_mask | (artists == artists[query]), k)
            totals["same_mode"].append(float(np.mean([modes[i] == modes[query] for i in picked])))
            if genres[query]:
                known = [i for i in picked if genres[i]]
                if known:
                    totals["same_main_genre"].append(
                        float(np.mean([genres[i] == genres[query] for i in known]))
                    )
            if tags[query]:
                overlaps = [
                    len(tags[query] & tags[i]) / len(tags[query] | tags[i])
                    for i in picked
                    if tags[i]
                ]
                if overlaps:
                    totals["genre_tag_jaccard"].append(float(np.mean(overlaps)))
            if decades[query]:
                known = [i for i in picked if decades[i]]
                if known:
                    totals["same_decade"].append(
                        float(np.mean([decades[i] == decades[query] for i in known]))
                    )
        report[name] = {
            metric: {"mean": round(float(np.mean(values)), 4), "queries": len(values)}
            for metric, values in sorted(totals.items())
        }
    return {"songs": count, "queries": len(chosen), "k": k, "seed": seed, "arms": report}


def run_proxy(args: argparse.Namespace) -> None:
    out = Path(args.out)
    report = proxy_metrics(load_index(out), queries=args.queries, k=args.k)
    (out / "proxy_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    metrics = ["same_main_genre", "genre_tag_jaccard", "same_decade", "same_artist", "same_mode"]
    print(f"{report['songs']} songs, {report['queries']} queries, top {report['k']}")
    print(f"{'arm':<9}" + "".join(f"{metric:>19}" for metric in metrics))
    for name, values in report["arms"].items():
        cells = "".join(f"{values.get(m, {}).get('mean', float('nan')):>19.4f}" for m in metrics)
        print(f"{name:<9}{cells}")


# --------------------------------------------------------------------------
# listening sheet
# --------------------------------------------------------------------------


def _link(row: dict) -> str:
    return f"https://open.spotify.com/track/{row['spotify_id']}"


def _top_axes(row: dict, index: SongIndex, count: int = 3) -> str:
    """The perceptual axes on which this song sits furthest above the sample."""
    position = index.position[row["song_id"]]
    offset = len(AXES)
    scored = [
        (float(index.color[position, offset + i]), axis) for i, axis in enumerate(PERCEPTUAL_AXES)
    ]
    scored.sort(reverse=True)
    high = [f"{axis} {value:+.1f}sd" for value, axis in scored[:count] if value > 0.25]
    return ", ".join(high) if high else "no axis clearly above average"


def _describe(row: dict, index: SongIndex) -> str:
    genre = row["main_genre"] or row["genre"] or "unknown genre"
    return f"[{row['key']} ({row['camelot']}), {genre}]({_link(row)}) - {_top_axes(row, index)}"


def run_sheet(args: argparse.Namespace) -> None:
    """Neighbour lists and a blind A/X/Y triplet sheet for a human listener."""
    out = Path(args.out)
    index = load_index(out)
    rng = random.Random(SEED)
    by_genre: dict[str, list[dict]] = defaultdict(list)
    for row in index.rows:
        if row["main_genre"]:
            by_genre[row["main_genre"]].append(row)
    genres = sorted(by_genre, key=lambda name: (-len(by_genre[name]), name))
    queries: list[dict] = []
    while len(queries) < args.queries and genres:
        for genre in list(genres):
            pool = by_genre[genre]
            if not pool:
                genres.remove(genre)
                continue
            queries.append(pool.pop(rng.randrange(len(pool))))
            if len(queries) >= args.queries:
                break

    lines = [
        "# Similar-song listening sheet",
        "",
        "Prototype output. Matches use chords only: no tempo, sound or lyrics.",
        "Each line is `key (Camelot), genre` linking to the track, then the three",
        "harmonic-color axes on which the song sits highest against the sample.",
        "",
    ]
    triplets, answers = [], []
    for number, query in enumerate(queries, start=1):
        neighbours = index.neighbours(query["song_id"], k=args.k)
        lines += [f"## {number}. {_describe(query, index)}", ""]
        lines += [f"{rank}. {_describe(row, index)}" for rank, row in enumerate(neighbours, 1)]
        lines.append("")
        controls = [
            row
            for row in by_genre[query["main_genre"]]
            if row["mode"] == query["mode"]
            and row["artist_id"] != query["artist_id"]
            and row["song_id"] != neighbours[0]["song_id"]
        ]
        if not neighbours or not controls:
            continue
        match, control = neighbours[0], rng.choice(controls)
        match_is_x = rng.random() < 0.5
        x, y = (match, control) if match_is_x else (control, match)
        triplets.append(
            {"triplet": number, "A": _link(query), "X": _link(x), "Y": _link(y), "closer_to_A": ""}
        )
        answers.append({"triplet": number, "system_pick": "X" if match_is_x else "Y"})

    (out / "listening_sheet.md").write_text("\n".join(lines), encoding="utf-8")
    for name, rows in (("triplets.csv", triplets), ("triplets_key.csv", answers)):
        with (out / name).open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]) if rows else ["triplet"])
            writer.writeheader()
            writer.writerows(rows)
    print(f"wrote {len(queries)} neighbour lists and {len(triplets)} triplets to {out}")


def run_similar(args: argparse.Namespace) -> None:
    index = load_index(Path(args.out))
    if args.song_id not in index.position:
        raise SystemExit(f"song {args.song_id} is not in the fingerprint sample")
    weights = dict(DEFAULT_WEIGHTS)
    for item in args.weight or []:
        name, _, value = item.partition("=")
        if name not in weights:
            raise SystemExit(f"unknown component {name!r}; choose from {COMPONENTS}")
        weights[name] = float(value)
    print("query:", _describe(index.rows[index.position[args.song_id]], index))
    neighbours = index.neighbours(
        args.song_id, k=args.k, weights=weights, camelot_compatible=args.camelot
    )
    for rank, row in enumerate(neighbours, start=1):
        print(f"{rank:>2}. {row['score']:+.2f}  {_describe(row, index)}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    commands = parser.add_subparsers(dest="command", required=True)

    build = commands.add_parser("build", help="fingerprint a deterministic sample of songs")
    build.add_argument("--sections", default=str(DEFAULT_SECTIONS))
    build.add_argument("--ngrams", default=str(DEFAULT_NGRAMS))
    build.add_argument("--raw", default=str(DEFAULT_RAW))
    build.add_argument("--songs", type=int, default=5000)
    build.add_argument("--workers", type=int, default=1)
    build.add_argument("--embed-sections", type=int, default=200_000)
    build.add_argument("--no-predictor", action="store_true")
    build.set_defaults(run=run_build)

    proxy = commands.add_parser("proxy", help="metadata agreement of neighbours vs random")
    proxy.add_argument("--queries", type=int, default=1000)
    proxy.add_argument("--k", type=int, default=10)
    proxy.set_defaults(run=run_proxy)

    sheet = commands.add_parser("sheet", help="neighbour lists and blind triplets for a listener")
    sheet.add_argument("--queries", type=int, default=30)
    sheet.add_argument("--k", type=int, default=5)
    sheet.set_defaults(run=run_sheet)

    similar = commands.add_parser("similar", help="neighbours of one sampled song")
    similar.add_argument("--song-id", required=True)
    similar.add_argument("--k", type=int, default=10)
    similar.add_argument("--camelot", action="store_true", help="only mix-compatible keys")
    similar.add_argument("--weight", action="append", metavar="COMPONENT=VALUE")
    similar.set_defaults(run=run_similar)
    return parser


def main(argv: Iterable[str] | None = None) -> None:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    args.run(args)


if __name__ == "__main__":
    main()
