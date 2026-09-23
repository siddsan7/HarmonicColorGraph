"""F11: 24-key probabilistic key finder.

Pitch-class salience -> correlation against a rotated major/minor key
profile, plus a diatonic chord-fit term and cadence evidence, combined into
a linear score and turned into a calibrated probability distribution over
all 24 major/minor keys via softmax. Weights and temperature are fit on the
dev half of `data/gold/keys.jsonl` and frozen in `keys_params.json`
(see `pipeline/stages/calibrate_keys.py`).
"""

import json
import math
from dataclasses import dataclass
from pathlib import Path

from app.schemas import CanonicalChord

# Krumhansl & Kessler (1982) and Temperley's (1999) revised "Kostka-Payne"
# key profiles, both widely reproduced in MIR literature. Kept behind the
# `profile` param so either can be selected; the frozen params choose one.
KRUMHANSL_MAJOR = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
KRUMHANSL_MINOR = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]
TEMPERLEY_MAJOR = [5.0, 2.0, 3.5, 2.0, 4.5, 4.0, 2.0, 4.5, 2.0, 3.5, 1.5, 4.0]
TEMPERLEY_MINOR = [5.0, 2.0, 3.5, 4.5, 2.0, 4.0, 2.0, 4.5, 3.5, 2.0, 1.5, 4.0]

PROFILES: dict[str, tuple[list[float], list[float]]] = {
    "krumhansl": (KRUMHANSL_MAJOR, KRUMHANSL_MINOR),
    "temperley": (TEMPERLEY_MAJOR, TEMPERLEY_MINOR),
}

NATURAL_MINOR = frozenset({0, 2, 3, 5, 7, 8, 10})
HARMONIC_MINOR = frozenset({0, 2, 3, 5, 7, 8, 11})
MELODIC_MINOR_ASCENDING = frozenset({0, 2, 3, 5, 7, 9, 11})
MINOR_UNION = NATURAL_MINOR | HARMONIC_MINOR | MELODIC_MINOR_ASCENDING
MAJOR_SCALE = frozenset({0, 2, 4, 5, 7, 9, 11})

# Salience weight by chord-tone position (root, 3rd, 5th, 7th, 9th, 11th, 13th).
POSITION_WEIGHT = [1.0, 0.8, 0.5, 0.6, 0.3, 0.3, 0.3]
BASS_BONUS = 0.5

# One-accidental-max canonical name per pitch class (the usual circle-of-fifths
# choice: flats for 1/3/8/10/11's neighbors, F# over Gb at the sharp/flat
# midpoint), so key labels read as "Eb major" rather than the enharmonically
# equivalent but unconventional "D# major".
CANONICAL_TONIC_NAME = [
    "C",
    "Db",
    "D",
    "Eb",
    "E",
    "F",
    "F#",
    "G",
    "Ab",
    "A",
    "Bb",
    "B",
]

PARAMS_PATH = Path(__file__).resolve().parent / "keys_params.json"

DEFAULT_PARAMS = {
    "profile": "krumhansl",
    "weights": {
        "profile_correlation": 1.0,
        "chord_fit": 1.0,
        "cadence_count": 0.5,
        "final_is_tonic": 0.5,
        "first_is_tonic": 0.2,
        "minor_plagal": 0.8,
    },
    "temperature": 0.35,
}


@dataclass(frozen=True)
class KeyCandidate:
    tonic_pc: int
    mode: str  # "major" | "minor"

    @property
    def key(self) -> str:
        return f"{CANONICAL_TONIC_NAME[self.tonic_pc]} {self.mode}"


ALL_CANDIDATES: list[KeyCandidate] = [
    KeyCandidate(tonic_pc=pc, mode=mode) for pc in range(12) for mode in ("major", "minor")
]


@dataclass(frozen=True)
class KeyEstimate:
    key: str
    tonic_pc: int
    mode: str
    probability: float


@dataclass(frozen=True)
class KeyEstimateResult:
    estimates: list[KeyEstimate]  # all 24 candidates, descending probability
    context_ambiguous: bool = False

    @property
    def best(self) -> KeyEstimate:
        return self.estimates[0]

    @property
    def ambiguous(self) -> bool:
        return _is_ambiguous(self.estimates) or self.context_ambiguous

    def top(self, n: int) -> list[KeyEstimate]:
        return self.estimates[:n]

    def probability_of(self, key: str) -> float:
        for estimate in self.estimates:
            if estimate.key == key:
                return estimate.probability
        return 0.0


def load_params() -> dict:
    if PARAMS_PATH.exists():
        return json.loads(PARAMS_PATH.read_text(encoding="utf-8"))
    return DEFAULT_PARAMS


def salience_vector(chords: list[CanonicalChord]) -> list[float]:
    """Per-pitch-class salience: root/3rd/5th/7th/extension weight from every
    chord tone, plus a bonus for whichever pitch class is in the bass.
    """
    salience = [0.0] * 12
    for chord in chords:
        for position, pc in enumerate(chord.pitch_classes):
            weight = POSITION_WEIGHT[min(position, len(POSITION_WEIGHT) - 1)]
            salience[pc % 12] += weight
        bass_pc = chord.bass_pc if chord.bass_pc is not None else chord.root_pc
        if bass_pc is not None:
            salience[bass_pc % 12] += BASS_BONUS
    return salience


def _pearson_correlation(a: list[float], b: list[float]) -> float:
    n = len(a)
    mean_a = sum(a) / n
    mean_b = sum(b) / n
    covariance = sum((x - mean_a) * (y - mean_b) for x, y in zip(a, b, strict=True))
    variance_a = sum((x - mean_a) ** 2 for x in a)
    variance_b = sum((y - mean_b) ** 2 for y in b)
    denominator = math.sqrt(variance_a * variance_b)
    return covariance / denominator if denominator else 0.0


def _rotate_profile_to_absolute_pcs(profile: list[float], tonic_pc: int) -> list[float]:
    return [profile[(pc - tonic_pc) % 12] for pc in range(12)]


def _chord_fit_share(chords: list[CanonicalChord], tonic_pc: int, mode: str) -> float:
    if not chords:
        return 0.0
    hits = 0
    for chord in chords:
        core_pcs = {(pc - tonic_pc) % 12 for pc in chord.pitch_classes[:3]}
        if mode == "major":
            scale = MAJOR_SCALE
        else:
            root_degree = (chord.root_pc - tonic_pc) % 12
            is_dominant_or_leading_tone_role = root_degree == 7 or chord.quality_class in (
                "dim",
                "dim7",
                "hdim7",
            )
            scale = MINOR_UNION if is_dominant_or_leading_tone_role else NATURAL_MINOR
        if core_pcs.issubset(scale):
            hits += 1
    return hits / len(chords)


def _cadence_features(chords: list[CanonicalChord], tonic_pc: int) -> tuple[float, float, float]:
    cadence_count = 0.0
    for current, following in zip(chords, chords[1:], strict=False):
        current_degree = (current.root_pc - tonic_pc) % 12
        following_degree = (following.root_pc - tonic_pc) % 12
        is_dominant_quality = current.quality_class in ("dom7", "maj", "aug")
        if current_degree == 7 and is_dominant_quality and following_degree == 0:
            cadence_count += 1.0
    final_is_tonic = 1.0 if chords and (chords[-1].root_pc - tonic_pc) % 12 == 0 else 0.0
    first_is_tonic = 1.0 if chords and (chords[0].root_pc - tonic_pc) % 12 == 0 else 0.0
    return cadence_count, final_is_tonic, first_is_tonic


def _minor_plagal_count(chords: list[CanonicalChord], tonic_pc: int) -> float:
    return float(
        sum(
            current.root_pc == (tonic_pc + 5) % 12
            and current.quality_class in {"min", "min7"}
            and following.root_pc == tonic_pc
            and following.quality_class in {"maj", "maj7"}
            for current, following in zip(chords, chords[1:], strict=False)
        )
    )


def score_candidate(
    chords: list[CanonicalChord],
    salience: list[float],
    candidate: KeyCandidate,
    params: dict,
) -> float:
    profile_major, profile_minor = PROFILES[params["profile"]]
    profile = profile_major if candidate.mode == "major" else profile_minor
    aligned_profile = _rotate_profile_to_absolute_pcs(profile, candidate.tonic_pc)
    profile_correlation = _pearson_correlation(salience, aligned_profile)
    chord_fit = _chord_fit_share(chords, candidate.tonic_pc, candidate.mode)
    cadence_count, final_is_tonic, first_is_tonic = _cadence_features(chords, candidate.tonic_pc)

    weights = params["weights"]
    return (
        weights["profile_correlation"] * profile_correlation
        + weights["chord_fit"] * chord_fit
        + weights["cadence_count"] * cadence_count
        + weights["final_is_tonic"] * final_is_tonic
        + weights["first_is_tonic"] * first_is_tonic
        + weights.get("minor_plagal", 0.0) * _minor_plagal_count(chords, candidate.tonic_pc)
    )


def estimate_keys(chords: list[CanonicalChord], params: dict | None = None) -> KeyEstimateResult:
    """Score all 24 major/minor keys for `chords` and return a calibrated
    probability distribution, sorted descending.
    """
    if params is None:
        params = load_params()
    if not chords:
        uniform = 1.0 / len(ALL_CANDIDATES)
        return KeyEstimateResult(
            estimates=[
                KeyEstimate(key=c.key, tonic_pc=c.tonic_pc, mode=c.mode, probability=uniform)
                for c in ALL_CANDIDATES
            ]
        )

    salience = salience_vector(chords)
    scores = {
        candidate: score_candidate(chords, salience, candidate, params)
        for candidate in ALL_CANDIDATES
    }
    # The gold calibration uses short templates. Long songs accumulate far
    # more evidence, and a fixed temperature makes their posterior overconfident.
    # Widen it smoothly after eight chords without changing candidate ranking.
    temperature = params["temperature"] * min(2.0, max(1.0, len(chords) / 8.0))
    max_score = max(scores.values())
    exp_scores = {
        candidate: math.exp((score - max_score) / temperature)
        for candidate, score in scores.items()
    }
    total = sum(exp_scores.values())
    estimates = sorted(
        (
            KeyEstimate(
                key=candidate.key,
                tonic_pc=candidate.tonic_pc,
                mode=candidate.mode,
                probability=exp_scores[candidate] / total,
            )
            for candidate in ALL_CANDIDATES
        ),
        key=lambda estimate: estimate.probability,
        reverse=True,
    )
    best = estimates[0]
    # A two-chord fragment, or a short phrase ending on V without resolution,
    # lacks enough cadence evidence to claim a settled key even if the profile
    # posterior is sharp. This is additive to the calibrated margin rule.
    context_ambiguous = len(chords) < 3 or (
        len(chords) <= 4 and (chords[-1].root_pc - best.tonic_pc) % 12 == 7 and best.mode == "major"
    )
    return KeyEstimateResult(estimates=estimates, context_ambiguous=context_ambiguous)


# Below this top1-vs-top2 probability margin, the key is not decisively
# settled. Calibrated empirically against data/gold/keys.jsonl: every item
# whose correct answer needed a real cadence or repeated tonic to lock in
# (rather than chord vocabulary alone, which a plain relative-major/minor
# pair always satisfies for both keys) fell below ~0.80; every item with a
# clear cadence or first/last-chord tonic landed above ~0.86, so 0.80 is the
# gap in between with no borderline gold item on either side of it.
AMBIGUOUS_PROBABILITY_MARGIN = 0.15


def _is_ambiguous(estimates: list[KeyEstimate]) -> bool:
    if len(estimates) < 2:
        return False
    top1, top2 = estimates[0], estimates[1]
    if top1.probability - top2.probability < AMBIGUOUS_PROBABILITY_MARGIN:
        return True
    if {top1.mode, top2.mode} == {"major", "minor"}:
        major_estimate = top1 if top1.mode == "major" else top2
        minor_estimate = top1 if top1.mode == "minor" else top2
        is_relative_pair = (major_estimate.tonic_pc - minor_estimate.tonic_pc) % 12 == 3
        if is_relative_pair and top2.probability > 0.3:
            return True
    return False


@dataclass(frozen=True)
class ModulationEvent:
    section_index: int
    from_key: str
    to_key: str
    semitones: int
    description: str


@dataclass(frozen=True)
class SongKeyResult:
    song_key: str
    song_key_estimate: KeyEstimateResult
    section_keys: list[str]
    section_estimates: list[KeyEstimateResult]
    modulations: list[ModulationEvent]


def estimate_song_keys(
    sections: list[list[CanonicalChord]],
    params: dict | None = None,
    repetition_weights: list[int] | None = None,
    section_names: list[str] | None = None,
) -> SongKeyResult:
    """Song key from every section's chords combined (repetition-weighted by
    inclusion); a section's local key overrides the song key only when it is
    both clearly stronger (>0.30 probability margin) and has enough chords
    (>=4) to be evidence rather than noise.
    """
    if params is None:
        params = load_params()

    if repetition_weights is None:
        repetition_weights = [1] * len(sections)
    if len(repetition_weights) != len(sections) or any(weight < 1 for weight in repetition_weights):
        raise ValueError("repetition_weights must have one positive value per section")
    if section_names is not None and len(section_names) != len(sections):
        raise ValueError("section_names must align with sections")
    unique_sections: dict[tuple[str, ...], tuple[list[CanonicalChord], int]] = {}
    for section, weight in zip(sections, repetition_weights, strict=True):
        signature = tuple(chord.symbol for chord in section)
        previous = unique_sections.get(signature)
        unique_sections[signature] = (section, weight + (previous[1] if previous else 0))
    all_chords = [
        chord
        for section, weight in unique_sections.values()
        for _ in range(weight)
        for chord in section
    ]
    song_estimate = estimate_keys(all_chords, params)
    song_key = song_estimate.best.key

    section_keys: list[str] = []
    section_estimates: list[KeyEstimateResult] = []
    modulations: list[ModulationEvent] = []

    for index, section in enumerate(sections):
        section_estimate = estimate_keys(section, params)
        local_best = section_estimate.best
        song_key_probability = section_estimate.probability_of(song_key)
        use_local_key = len(section) >= 4 and local_best.probability - song_key_probability > 0.30
        chosen_key = local_best.key if use_local_key else song_key
        section_keys.append(chosen_key)
        section_estimates.append(section_estimate)
        if use_local_key and chosen_key != song_key:
            shift = (local_best.tonic_pc - song_estimate.best.tonic_pc) % 12
            signed_shift = shift if shift <= 6 else shift - 12
            location = section_names[index] if section_names else f"section {index + 1}"
            modulations.append(
                ModulationEvent(
                    section_index=index,
                    from_key=song_key,
                    to_key=chosen_key,
                    semitones=signed_shift,
                    description=f"{signed_shift:+d} semitones in {location}",
                )
            )

    return SongKeyResult(
        song_key=song_key,
        song_key_estimate=song_estimate,
        section_keys=section_keys,
        section_estimates=section_estimates,
        modulations=modulations,
    )
