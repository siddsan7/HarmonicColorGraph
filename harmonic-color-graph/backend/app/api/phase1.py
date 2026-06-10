from typing import Annotated

from fastapi import APIRouter, Query

from app.schemas import (
    AnalyzeProgressionRequest,
    AnalyzeProgressionResponse,
    ExplainTransitionResponse,
    NextChordsResponse,
    TransitionStatsResponse,
)
from app.services.analysis import analyze_progression_service
from app.services.transition_graph import ProgressionTransitionInput, aggregate_transitions
from app.services.transition_lookup import get_next_chords, get_transition_stats
from app.theory.relationships import label_transition

router = APIRouter(tags=["phase-1"])

DEMO_TRANSITIONS = aggregate_transitions(
    [
        ProgressionTransitionInput(
            roman_chords=["I", "V", "vi", "IV"],
            genre="pop",
            section="chorus",
        ),
        ProgressionTransitionInput(
            roman_chords=["I", "V", "vi", "IV"],
            genre="pop",
            section="chorus",
        ),
        ProgressionTransitionInput(roman_chords=["I", "V", "I"]),
        ProgressionTransitionInput(roman_chords=["ii", "V", "I"], genre="jazz"),
        ProgressionTransitionInput(roman_chords=["I", "bII7", "I"]),
    ]
)


@router.post("/analyze-progression", response_model=AnalyzeProgressionResponse)
def analyze_progression_endpoint(
    request: AnalyzeProgressionRequest,
) -> AnalyzeProgressionResponse:
    return analyze_progression_service(request.chords, key=request.key)


@router.get("/next-chords", response_model=NextChordsResponse)
def next_chords_endpoint(
    progression: Annotated[str, Query(min_length=1)],
    genre: str | None = None,
    section: str | None = None,
) -> NextChordsResponse:
    roman_progression = [
        chord.strip() for chord in progression.split(",") if chord.strip()
    ]
    return get_next_chords(
        roman_progression,
        DEMO_TRANSITIONS,
        genre=genre,
        section=section,
    )


@router.get("/explain-transition", response_model=ExplainTransitionResponse)
def explain_transition_endpoint(
    from_roman: Annotated[str, Query(alias="from", min_length=1)],
    to_roman: Annotated[str, Query(alias="to", min_length=1)],
    mode: str = "major",
) -> ExplainTransitionResponse:
    transition = label_transition(from_roman, to_roman, mode)
    return ExplainTransitionResponse(
        from_roman=from_roman,
        to_roman=to_roman,
        labels=transition.relationship_labels,
        short_explanation=transition.short_explanation or "",
        technical_explanation=transition.technical_explanation or "",
    )


@router.get("/transition-stats", response_model=TransitionStatsResponse)
def transition_stats_endpoint(
    from_roman: Annotated[str, Query(alias="from", min_length=1)],
    genre: str | None = None,
    section: str | None = None,
) -> TransitionStatsResponse:
    return get_transition_stats(
        from_roman,
        DEMO_TRANSITIONS,
        genre=genre,
        section=section,
    )
