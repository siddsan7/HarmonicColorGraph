"""Fast, deterministic ranking features for a candidate next function."""

from __future__ import annotations

import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass

from app.color.features import compute_chord_color
from app.color.norms import NormsTable, normalize
from app.predict.realize import realize
from app.recommend.candidates import Candidate
from app.theory.roman import romanize_chord
from app.theory.spelling import lof

FEATURE_NAMES = (
    "log_p_ngram",
    "log_p_global_bigram",
    "pmi",
    "diatonic",
    "borrowed",
    "applied",
    "tritone_sub",
    "chromatic_mediant",
    "vl_cost",
    "common_tones",
    "emb_cos",
    "tonal_distance",
    "surprise",
    "genre_section_fit",
    "graph_probability",
    "delta_brightness",
    "delta_tension",
    "delta_surprise",
    "delta_complexity",
    "delta_resolution",
    "delta_smoothness",
)
COLOR_AXES = ("brightness", "tension", "surprise", "complexity", "resolution", "smoothness")
_FIGURE_BASE = re.compile(r"^(?:b|#)?(?:VII|VI|IV|III|II|I|V|vii|vi|iv|iii|ii|i|v)")
_BORROWED_BY_MODE = {"M": {"iv", "bVI", "bVII", "bIII", "i"}, "m": {"IV", "V", "I", "II"}}


@dataclass(frozen=True)
class CandidateFeatures:
    token: str
    values: dict[str, float]
    color_delta: dict[str, float]


def _clip(value: float, low: float = -1.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _color_values(raw: object, norms: NormsTable | None) -> dict[str, float]:
    values = asdict(raw)
    result = {}
    for axis in COLOR_AXES:
        value = values[axis]
        if value is None:
            result[axis] = 0.0
        elif norms and (axis, "transition") in norms:
            result[axis] = normalize(value, norms[(axis, "transition")])
        elif axis == "surprise":
            result[axis] = _clip(value / 16.0, 0.0, 1.0)
        else:
            result[axis] = _clip(value, 0.0, 1.0)
    return result


def extract_features(
    candidate: Candidate,
    history: Sequence[str],
    key: str,
    *,
    global_bigram: Mapping[str, float] | None = None,
    global_unigram: Mapping[str, float] | None = None,
    context_probability: float | None = None,
    norms: NormsTable | None = None,
) -> CandidateFeatures:
    """Compute theory, motion, corpus and color features without I/O.

    Probability maps are optional. Missing graph/vector/corpus evidence has an
    explicit zero feature rather than falsely claiming evidence. The n-gram
    probability floor applies only to logs and surprise, not plausibility.
    """
    if not history:
        raise ValueError("Feature extraction needs a previous chord")
    previous = realize(history[-1], key).chord
    current = realize(candidate.token, key).chord
    previous_token = romanize_chord(previous, key)
    current_token = romanize_chord(current, key, previous_chord=previous)
    previous_color = compute_chord_color(previous, previous_token, key)
    current_color = compute_chord_color(
        current, current_token, key, previous_chord=previous, previous_token=previous_token
    )
    old_color = _color_values(previous_color, norms)
    new_color = _color_values(current_color, norms)
    ngram_p = candidate.ngram_probability
    bigram_p = (global_bigram or {}).get(candidate.token, 0.0)
    unigram_p = (global_unigram or {}).get(candidate.token, 0.0)
    surprise = _clip(-math.log2(max(ngram_p, 1e-6)) / 16.0, 0.0, 1.0)
    new_color["surprise"] = surprise
    old_color["surprise"] = 0.0  # last chord's historical surprise is not known here
    delta = {axis: _clip(new_color[axis] - old_color[axis]) for axis in COLOR_AXES}
    overlap = len(set(previous.pitch_classes) & set(current.pitch_classes))
    root_fifths = abs(lof(previous.root) - lof(current.root))
    mode, figure = candidate.token.split(":", 1)
    match = _FIGURE_BASE.match(figure)
    base_figure = match.group(0) if match else figure
    is_applied = "/" in figure
    is_sub = figure.startswith("subV")
    is_borrowed = not is_applied and base_figure in _BORROWED_BY_MODE[mode]
    is_mediant = not is_applied and base_figure in {"bIII", "bVI", "III", "VI"}
    # Color smoothness uses the F40 voicing engine and is therefore the
    # authoritative motion measurement; no second voice-leading search.
    vl_cost = 1.0 - new_color["smoothness"]
    values = {
        "log_p_ngram": math.log(max(ngram_p, 1e-6)) / 14.0,
        "log_p_global_bigram": math.log(max(bigram_p, 1e-6)) / 14.0,
        "pmi": _clip(math.log(max(bigram_p, 1e-6) / max(unigram_p, 1e-6)) / 6.0),
        "diatonic": float(not is_applied and not is_borrowed and not current_token.is_chromatic),
        "borrowed": float(is_borrowed),
        "applied": float(is_applied),
        "tritone_sub": float(is_sub),
        "chromatic_mediant": float(is_mediant),
        "vl_cost": vl_cost,
        "common_tones": overlap / max(len(set(current.pitch_classes)), 1),
        "emb_cos": candidate.embedding_similarity or 0.0,
        "tonal_distance": _clip(root_fifths / 7.0, 0.0, 1.0),
        "surprise": surprise,
        "genre_section_fit": _clip(
            math.log(max(context_probability or 0.0, 1e-6) / max(bigram_p, 1e-6)) / 6.0
        )
        if context_probability is not None
        else 0.0,
        "graph_probability": candidate.graph_probability,
    }
    values.update({f"delta_{axis}": delta[axis] for axis in COLOR_AXES})
    assert tuple(values) == FEATURE_NAMES
    return CandidateFeatures(candidate.token, values, delta)
