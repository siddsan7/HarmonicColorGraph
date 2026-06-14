from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.repositories import HarmonicRepository
from app.db.session import get_session
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
    session: Session = Depends(get_session),
) -> NextChordsResponse:
    roman_progression = [
        chord.strip() for chord in progression.split(",") if chord.strip()
    ]
    records, data_source, fallback_used, database_count = _transition_records_for_lookup(
        roman_progression[-1],
        session=session,
    )
    response = get_next_chords(
        roman_progression,
        records,
        genre=genre,
        section=section,
    )
    response.data_source = data_source
    response.fallback_used = fallback_used
    response.database_transition_count = database_count
    return response


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
    session: Session = Depends(get_session),
) -> TransitionStatsResponse:
    records, data_source, fallback_used, database_count = _transition_records_for_lookup(
        from_roman,
        session=session,
    )
    response = get_transition_stats(
        from_roman,
        records,
        genre=genre,
        section=section,
    )
    response.data_source = data_source
    response.fallback_used = fallback_used
    response.database_transition_count = database_count
    return response


def _transition_records_for_lookup(
    from_roman: str,
    *,
    session: Session,
):
    repository = HarmonicRepository(session)
    database_records = repository.list_transition_records_from(from_roman)
    if database_records:
        return database_records, "database", False, len(database_records)

    if get_settings().demo_fallback_enabled:
        demo_records = [
            transition
            for transition in DEMO_TRANSITIONS
            if transition.from_roman == from_roman
        ]
        return demo_records, "demo_fallback", True, 0

    return [], "database_empty", False, 0
