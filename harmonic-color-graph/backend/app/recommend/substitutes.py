"""Bidirectional, explainable substitutions for a single progression position."""

from __future__ import annotations

import math
from collections.abc import Callable, Iterable
from typing import Protocol

from sqlalchemy.orm import Session

from app.predict.ngram import KNPredictor, PredictionResult
from app.predict.realize import realize
from app.schemas.substitutes_v2 import (
    Substitute,
    SubstituteData,
    SubstituteRequest,
    SubstituteResponse,
    SubstituteScore,
)
from app.services.recommend import SessionNgramReader, _input_tokens
from app.theory.roman import analyze_v2
from app.theory.voice_leading import transition_metrics, voice_lead


class Candidate(Protocol):
    token: str


CandidateGenerator = Callable[[list[str], str, PredictionResult], Iterable[Candidate]]


def _shared_candidates(
    history: list[str], key: str, prediction: PredictionResult
) -> Iterable[Candidate]:
    # Import when called so the F52 candidate service is the one shared source.
    # The API remains importable while a deployment is rolling from F52 to F53.
    from app.recommend.candidates import generate_candidates

    return generate_candidates(history, key, prediction)


def _motion(chords: list[str], index: int, replacement: str) -> int:
    relevant = chords[max(0, index - 1) : min(len(chords), index + 2)].copy()
    relevant[index - max(0, index - 1)] = replacement
    path = voice_lead(relevant, "root_position")
    return sum(
        transition_metrics(first, second).total_motion
        for first, second in zip(path, path[1:], strict=False)
    )


class SubstitutionService:
    def __init__(
        self, predictor: KNPredictor, candidate_generator: CandidateGenerator = _shared_candidates
    ) -> None:
        self.predictor = predictor
        self.candidate_generator = candidate_generator

    @classmethod
    def from_session(cls, session: Session) -> SubstitutionService:
        return cls(KNPredictor(SessionNgramReader(session)))

    def find(self, request: SubstituteRequest) -> SubstituteResponse:
        version = self.predictor.store.active_version()
        if version is None:
            raise LookupError("No corpus version is active")
        tokens, key, warnings = _input_tokens(request.progression, request.key)
        if request.index >= len(tokens):
            raise ValueError("index must refer to a chord in the progression")
        chords = [realize(token, key).chord.raw_symbol for token in tokens]
        index = request.index
        original = tokens[index]
        left = tokens[:index]
        right = tokens[index + 1 :]
        prediction = self.predictor.predict(left, top_n=100)
        forward = {item.token: item.probability for item in prediction.predictions}
        candidates = list(self.candidate_generator(left, key, prediction))
        candidate_tokens = list(dict.fromkeys(item.token for item in candidates))
        # Bound the number of conditional KN reads even when theory expansion
        # creates more candidates than the online latency budget can support.
        candidate_tokens = candidate_tokens[:24]
        original_function = analyze_v2([chords[index]], key).tokens[0].function
        original_cost = _motion(chords, index, chords[index])
        ranked: list[Substitute] = []
        for token in candidate_tokens:
            if token == original or token[0] != original[0]:
                continue
            try:
                realized = realize(token, key).chord
                chord = realized.raw_symbol
                function = analyze_v2([chord], key).tokens[0].function
                motion = _motion(chords, index, chord)
            except ValueError:
                continue
            if request.constraints.keep_function and function != original_function:
                continue
            if request.constraints.smooth and motion > original_cost + 3:
                continue
            left_p = max(forward.get(token, 0.0), 1e-9)
            right_p = 1.0
            if right:
                right_p = max(self.predictor.distribution([*left, token]).get(right[0], 0), 1e-9)
            # Function is a soft equivalence bonus, never a fabricated graph fact.
            function_bonus = 0.75 if function == original_function else 0.0
            smoothness = -0.025 * motion
            surprise = -math.log(left_p) * 0.15 if request.constraints.surprise else 0.0
            left_log = math.log(left_p)
            right_log = math.log(right_p)
            total = left_log + right_log + function_bonus + smoothness + surprise
            reasons = [
                f"Corpus likelihood: {left_p:.1%} after the preceding harmony.",
            ]
            if right:
                reasons.append(f"Continuation to {chords[index + 1]}: {right_p:.1%}.")
            if function_bonus:
                reasons.append(f"Keeps the {original_function} harmonic function.")
            if motion < original_cost:
                reasons.append(f"Voice motion improves by {original_cost - motion} semitones.")
            if request.constraints.surprise:
                reasons.append("Rewards a less expected substitution.")
            ranked.append(
                Substitute(
                    token=token,
                    chord=chord,
                    pitch_classes=realized.pitch_classes,
                    score=total,
                    score_breakdown=SubstituteScore(
                        left_log_probability=left_log,
                        right_log_probability=right_log,
                        function_bonus=function_bonus,
                        smoothness=smoothness,
                        surprise=surprise,
                        total=total,
                    ),
                    voice_leading_cost=motion,
                    reasons=reasons,
                )
            )
        ranked.sort(key=lambda item: (-item.score, item.token))
        return SubstituteResponse(
            data=SubstituteData(
                index=index,
                original_chord=chords[index],
                key=key,
                substitutes=ranked[: request.k],
            ),
            meta={"corpus_version": version, "model": "bidirectional-kn-v1"},
            warnings=[item.message for item in warnings],
        )
