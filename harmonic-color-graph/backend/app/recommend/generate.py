"""Deterministic, bounded beam search over F52 n-gram and theory candidates."""

from __future__ import annotations

import math
import re
import time
from dataclasses import asdict, dataclass
from functools import lru_cache

from app.color.features import compute_chord_color
from app.ngram_contract import MAX_ORDER_GLOBAL
from app.predict.realize import realize
from app.recommend.candidates import generate_candidates
from app.schemas.generate_v2 import GeneratedPath, GeneratedStep, GenerateRequest, GenerateResponse
from app.services.recommend import RecommendationService, _context_value, _input_tokens
from app.theory.chord_normalizer import normalize_chord
from app.theory.relationships_v2 import analyze_relationships
from app.theory.roman import parse_key, romanize_chord
from app.theory.voice_leading import voice_lead

BEAM_WIDTH = 32
EXPANSIONS_PER_STATE = 16


@dataclass(frozen=True)
class _State:
    tokens: tuple[str, ...]
    symbols: tuple[str, ...]
    voicing: tuple[int, ...]
    colors: tuple[dict[str, float | None], ...]
    sources: tuple[frozenset[str], ...]
    score: float
    parts: tuple[dict[str, float], ...]


def _target_curve(request: GenerateRequest) -> list[float]:
    if request.tension_curve == "custom":
        return list(request.custom_curve or [])
    if request.tension_curve == "plateau":
        return [0.5] * request.length
    peak = (request.length - 1) / 2 if request.tension_curve == "arch" else request.length // 2
    return [
        index / peak
        if index <= peak
        else (request.length - 1 - index) / (request.length - 1 - peak)
        for index in range(request.length)
    ]


def _edit_distance(left: tuple[str, ...], right: tuple[str, ...]) -> int:
    previous = list(range(len(right) + 1))
    for index, token in enumerate(left, start=1):
        current = [index]
        for column, other in enumerate(right, start=1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[column] + 1,
                    previous[column - 1] + (token != other),
                )
            )
        previous = current
    return previous[-1]


def _required_token(value: str, key: str) -> str:
    tokens, _, _ = _input_tokens([value], key)
    return tokens[0]


def _required(value: str, key: str) -> tuple[str, str]:
    token = _required_token(value, key)
    if re.fullmatch(r"[Mm]:\S+", value):
        return token, _chord(token, key)[0].raw_symbol
    parsed = normalize_chord(value)
    if not parsed.success or parsed.chord is None:
        raise ValueError(f"Unsupported required chord: {value}")
    return token, parsed.chord.raw_symbol


@lru_cache(maxsize=1024)
def _chord(token: str, key: str):
    realized = realize(token, key).chord
    return realized, romanize_chord(realized, key)


@lru_cache(maxsize=1024)
def _symbol_chord(symbol: str):
    parsed = normalize_chord(symbol)
    if not parsed.success or parsed.chord is None:
        raise ValueError(f"Unsupported chord: {symbol}")
    return parsed.chord


@lru_cache(maxsize=1024)
def _seed_voicing(symbol: str) -> tuple[int, ...]:
    """Playable state voicing; completed paths get a full voice-leading pass."""
    return tuple(voice_lead([_symbol_chord(symbol)], strategy="root_position")[0])


@lru_cache(maxsize=8192)
def _color(previous: str | None, current: str, key: str) -> dict[str, float | None]:
    current_chord = _symbol_chord(current)
    current_roman = romanize_chord(current_chord, key)
    if previous is None:
        raw = compute_chord_color(current_chord, current_roman, key)
    else:
        old_chord = _symbol_chord(previous)
        old_roman = romanize_chord(old_chord, key)
        raw = compute_chord_color(
            current_chord,
            current_roman,
            key,
            previous_chord=old_chord,
            previous_token=old_roman,
        )
    return asdict(raw)


class ProgressionGenerator:
    def __init__(self, service: RecommendationService):
        self.service = service

    def generate(self, request: GenerateRequest) -> GenerateResponse:
        started = time.perf_counter()
        version = self.service.predictor.store.active_version()
        if version is None:
            raise LookupError("No corpus version is active")
        _, mode, key = parse_key(request.key)
        prefix = "M" if mode == "major" else "m"
        required = {i: _required(value, key) for i, value in request.required_chords.items()}
        for index, value in ((0, request.start), (request.length - 1, request.end)):
            if value is not None:
                token, symbol = _required(value, key)
                if index in required and required[index] != (token, symbol):
                    raise ValueError(f"Conflicting required chord at position {index}")
                required[index] = (token, symbol)
        allowed = [_context_value(value) for value in request.allowed_genres or []]
        genre = _context_value(request.genre)
        if genre is None and allowed:
            genre = next(
                (
                    value
                    for value in allowed
                    if self.service.predictor.store.context_by_key(f"genre:{value}") is not None
                ),
                allowed[0],
            )
        if genre and self.service.predictor.store.context_by_key(f"genre:{genre}") is None:
            return GenerateResponse(
                key=key,
                genre=genre,
                paths=[],
                corpus_version=version,
                latency_ms=round((time.perf_counter() - started) * 1000, 2),
                warnings=[f"No retained corpus context for genre {genre}."],
            )
        curve = _target_curve(request)

        def chord(token: str):
            return _chord(token, key)

        def color(previous: str | None, current: str) -> dict[str, float | None]:
            return _color(previous, current, key)

        @lru_cache(maxsize=1024)
        def predict(suffix: tuple[str, ...]):
            return self.service.predictor.predict(suffix, genre=genre, top_n=30)

        beam = [_State((), (), (), (), (), 0.0, ())]
        for index in range(request.length):
            next_beam: list[_State] = []
            for state in beam:
                history = state.tokens
                prediction = predict(history[-(MAX_ORDER_GLOBAL - 1) :])
                pool = generate_candidates(history, key, prediction)
                chosen = pool[:EXPANSIONS_PER_STATE]
                forced = required.get(index)
                if forced is not None:
                    chosen = [item for item in pool if item.token == forced[0]]
                    if not chosen:
                        # A valid user token can be outside the finite theory
                        # vocabulary; it still participates as a theory option.
                        from app.recommend.candidates import Candidate

                        chosen = [Candidate(forced[0], frozenset({"required"}))]
                for item in chosen:
                    if not item.token.startswith(f"{prefix}:"):
                        continue
                    previous = state.tokens[-1] if state.tokens else None
                    previous_symbol = state.symbols[-1] if state.symbols else None
                    current_symbol = forced[1] if forced else chord(item.token)[0].raw_symbol
                    arc = color(previous_symbol, current_symbol)
                    if (
                        color(None, current_symbol)["chromaticity"] or 0.0
                    ) > request.max_chromaticity:
                        continue
                    if index == request.length - 1 and request.cadence != "any":
                        assert previous is not None
                        pair = [
                            romanize_chord(_symbol_chord(previous_symbol), key),
                            romanize_chord(_symbol_chord(current_symbol), key),
                        ]
                        ids = {fact.id for fact in analyze_relationships(pair)}
                        accepted = (
                            {"plagal", "minor_plagal"}
                            if request.cadence == "plagal"
                            else {request.cadence}
                        )
                        if not ids & accepted:
                            continue
                    # Theory expansions have no observed probability. A small
                    # explicit prior keeps them available to satisfy color
                    # goals without claiming corpus support.
                    plausibility = math.log(max(item.ngram_probability, 0.01))
                    curve_term = -12.0 * abs((arc["tension"] or 0.0) - curve[index])
                    color_term = -sum(
                        abs((arc[axis] or 0.0) - target)
                        for axis, target in request.color_target.items()
                    )
                    smooth_term = request.smoothness * (arc["smoothness"] or 0.0)
                    novelty_term = request.novelty * (1.0 - item.ngram_probability)
                    repetition_term = -2.0 if previous == item.token else 0.0
                    parts = {
                        "log_plausibility": plausibility,
                        "curve": curve_term,
                        "color": color_term,
                        "smoothness": smooth_term,
                        "novelty": novelty_term,
                        "repetition": repetition_term,
                    }
                    next_beam.append(
                        _State(
                            (*state.tokens, item.token),
                            (*state.symbols, current_symbol),
                            _seed_voicing(current_symbol),
                            (*state.colors, arc),
                            (*state.sources, item.generators),
                            state.score + sum(parts.values()),
                            (*state.parts, parts),
                        )
                    )
            next_beam.sort(key=lambda state: (-state.score, state.tokens))
            # The search itself stays width 32. Keep more terminal states for
            # MMR so near-identical high-scoring paths do not crowd out k.
            final_pool = max(BEAM_WIDTH, request.k * BEAM_WIDTH)
            beam = next_beam[: final_pool if index == request.length - 1 else BEAM_WIDTH]
            if not beam:
                break

        selected: list[_State] = []
        remaining = [state for state in beam if len(state.tokens) == request.length]
        while remaining and len(selected) < request.k:
            eligible = [
                state
                for state in remaining
                if all(_edit_distance(state.tokens, picked.tokens) >= 2 for picked in selected)
            ]
            if not eligible:
                break
            winner = max(
                eligible,
                key=lambda state: (
                    state.score
                    + 0.5
                    * min(
                        (_edit_distance(state.tokens, picked.tokens) for picked in selected),
                        default=0,
                    ),
                    state.tokens,
                ),
            )
            selected.append(winner)
            remaining.remove(winner)

        paths = []
        for state in selected:
            chords = [_symbol_chord(symbol) for symbol in state.symbols]
            romans = [romanize_chord(item, key, chord_index=i) for i, item in enumerate(chords)]
            voicings = voice_lead(chords)
            facts = analyze_relationships(romans)
            steps = []
            for index, (token, item, voicing, parts) in enumerate(
                zip(state.tokens, chords, voicings, state.parts, strict=True)
            ):
                arc = state.colors[index]
                leaders = sorted(parts.items(), key=lambda part: (-abs(part[1]), part[0]))[:2]
                contributions = ", ".join(f"{name} {value:+.2f}" for name, value in leaders)
                sources = sorted(state.sources[index])
                source_label = "corpus estimate" if "ngram" in sources else "theory option"
                steps.append(
                    GeneratedStep(
                        token=token,
                        chord=item.raw_symbol,
                        sources=sources,
                        pitch_classes=list(item.pitch_classes),
                        voicing=voicing,
                        color=arc,
                        score_breakdown=parts,
                        explanation=(
                            f"{item.raw_symbol} ({source_label}): "
                            f"main score contributions are {contributions}."
                        ),
                    )
                )
            paths.append(
                GeneratedPath(
                    tokens=list(state.tokens),
                    chords=[item.raw_symbol for item in chords],
                    steps=steps,
                    facts=facts,
                    score=state.score,
                )
            )
        warnings = []
        if len(paths) < request.k:
            warnings.append(
                f"Only {len(paths)} distinct paths satisfy the constraints (requested {request.k})."
            )
        return GenerateResponse(
            key=key,
            genre=genre,
            paths=paths,
            corpus_version=version,
            latency_ms=round((time.perf_counter() - started) * 1000, 2),
            warnings=warnings,
        )
