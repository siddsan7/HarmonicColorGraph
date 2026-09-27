"""F70: validated internal tools that call domain services, never HTTP endpoints."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.ai.schemas import (
    TOOL_MODELS,
    AnalyzeInput,
    ExamplesData,
    ExamplesInput,
    ExplainTransitionInput,
    GenerateInput,
    GraphEdge,
    GraphPathData,
    GraphPathInput,
    Path,
    PlaybackChord,
    PlaybackData,
    PlaybackInput,
    ProgressionInput,
    RecommendInput,
    SimilarInput,
    SongExample,
    SubstituteInput,
    ToolEvidence,
    ToolResult,
    TransitionData,
)
from app.db.stores.embeddings import EmbeddingStore
from app.db.stores.graph import GraphStore, PatternStore
from app.graph.service import GraphService
from app.recommend.generate import ProgressionGenerator
from app.recommend.substitutes import SubstitutionService
from app.schemas.analysis_v2 import AnalysisV2
from app.schemas.color_v2 import ColorProfileResponse
from app.schemas.generate_v2 import GenerateResponse
from app.schemas.recommend_v2 import RecommendResponse
from app.schemas.similar_v2 import SimilarResponse
from app.schemas.substitutes_v2 import SubstituteResponse
from app.services.color_profile import compute_color_profile
from app.services.recommend import RecommendationService
from app.services.similarity import SimilarityService
from app.theory.roman import analyze_v2
from app.theory.voice_leading import voice_lead


class ToolError(Exception):
    """Stable error category for workflow and MCP adapters."""

    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


@dataclass
class ToolServices:
    recommendations: RecommendationService
    substitutes: SubstitutionService
    similarity: SimilarityService
    graph: GraphService
    patterns: PatternStore

    @classmethod
    def from_session(cls, session: Session) -> ToolServices:
        return cls(
            recommendations=RecommendationService.from_session(session),
            substitutes=SubstitutionService.from_session(session),
            similarity=SimilarityService(EmbeddingStore(session)),
            graph=GraphService(GraphStore(session)),
            patterns=PatternStore(session),
        )


def _facts(*groups: list[str]) -> list[str]:
    return sorted({fact_id for group in groups for fact_id in group})


def _version(value: str | None) -> str:
    if value is None:
        raise LookupError("No corpus version is active")
    return value


def analyze_progression(request: AnalyzeInput) -> ToolResult[AnalysisV2]:
    data = analyze_v2(request.chords, request.key, request.section_markers)
    fact_ids = _facts(*(item.fact_ids for item in data.relationships))
    return ToolResult[AnalysisV2](
        data=data,
        fact_ids=fact_ids,
        evidence=[
            ToolEvidence(
                source="theory",
                subject=f"{item.from_index}->{item.to_index}",
                fact_ids=item.fact_ids,
            )
            for item in data.relationships
        ]
        or [ToolEvidence(source="theory", subject="analyzed progression")],
    )


def recommend_next(
    request: RecommendInput, service: RecommendationService
) -> ToolResult[RecommendResponse]:
    data = service.recommend(request)
    candidates = data.data.recommendations
    return ToolResult[RecommendResponse](
        data=data,
        fact_ids=_facts(*(item.fact_ids for item in candidates)),
        evidence=[
            ToolEvidence(
                source="corpus",
                subject=item.token,
                fact_ids=item.fact_ids,
                count=item.evidence.count,
            )
            for item in candidates
        ]
        or [ToolEvidence(source="corpus", subject="no recommendations", count=0)],
    )


def find_substitutes(
    request: SubstituteInput, service: SubstitutionService
) -> ToolResult[SubstituteResponse]:
    data = service.find(request)
    return ToolResult[SubstituteResponse](
        data=data,
        evidence=[
            ToolEvidence(source="corpus", subject=item.token) for item in data.data.substitutes
        ]
        or [ToolEvidence(source="corpus", subject="no substitutes", count=0)],
    )


def generate_progression(
    request: GenerateInput, service: RecommendationService
) -> ToolResult[GenerateResponse]:
    data = ProgressionGenerator(service).generate(request)
    facts = [fact for path in data.paths for fact in path.facts]
    return ToolResult[GenerateResponse](
        data=data,
        fact_ids=_facts(*(fact.fact_ids for fact in facts)),
        evidence=[
            ToolEvidence(source="theory", subject=fact.id, fact_ids=fact.fact_ids) for fact in facts
        ]
        or [ToolEvidence(source="corpus", subject="generated progression")],
    )


def _edge(row: dict[str, Any]) -> GraphEdge:
    return GraphEdge(
        source=row["src"],
        target=row["dst"],
        relationship=row["type"],
        probability=row.get("prob"),
        count=row.get("count"),
        fact_ids=list((row.get("props") or {}).get("fact_ids") or []),
    )


def explain_transition(
    request: ExplainTransitionInput, service: GraphService
) -> ToolResult[TransitionData]:
    raw = service.explain_edge(request.source, request.target, context=request.context)
    edges = [_edge(row) for row in raw["edges"]]
    data = TransitionData(
        source=edges[0].source,
        target=edges[0].target,
        edges=edges,
        count=raw["evidence"]["count"],
        support=raw["evidence"]["support"],
        corpus_version=_version(service.store.active_version()),
    )
    return ToolResult[TransitionData](
        data=data,
        fact_ids=_facts(*(edge.fact_ids for edge in edges)),
        evidence=[
            ToolEvidence(
                source="graph",
                subject=f"{edge.source}->{edge.target}",
                fact_ids=edge.fact_ids,
                count=edge.count,
            )
            for edge in edges
        ],
    )


def similar_progressions(
    request: SimilarInput, service: SimilarityService
) -> ToolResult[SimilarResponse]:
    data = service.progressions(request)
    return ToolResult[SimilarResponse](
        data=data,
        evidence=[
            ToolEvidence(source="corpus", subject=item.subject_id, count=item.support)
            for item in data.results
        ]
        or [ToolEvidence(source="corpus", subject=data.query, count=0)],
    )


def graph_path(request: GraphPathInput, service: GraphService) -> ToolResult[GraphPathData]:
    raw = service.paths(
        request.source,
        request.target,
        context=request.context,
        k=request.k,
        max_len=request.max_len,
        constraint=request.constraint,
        max_chromaticity=request.max_chromaticity,
    )
    paths = [
        Path(nodes=item["nodes"], edges=[_edge(edge) for edge in item["edges"]], cost=item["cost"])
        for item in raw
    ]
    edges = [edge for path in paths for edge in path.edges]
    return ToolResult[GraphPathData](
        data=GraphPathData(paths=paths, corpus_version=_version(service.store.active_version())),
        fact_ids=_facts(*(edge.fact_ids for edge in edges)),
        evidence=[
            ToolEvidence(
                source="graph",
                subject=f"{edge.source}->{edge.target}",
                fact_ids=edge.fact_ids,
                count=edge.count,
            )
            for edge in edges
        ]
        or [ToolEvidence(source="graph", subject="no path", count=0)],
    )


def get_examples(
    request: ExamplesInput, patterns: PatternStore, graph: GraphService
) -> ToolResult[ExamplesData]:
    version = _version(patterns.active_version())
    if graph.store.context_by_key(request.context) is None:
        raise ValueError(f"Unknown graph context: {request.context}")
    if request.pattern_tokens is not None:
        kind = "pattern"
        subject = " ".join(request.pattern_tokens)
        rows = patterns.examples(subject, context=request.context, limit=request.limit)
    else:
        assert request.transition is not None
        kind = "transition"
        source, target = request.transition
        subject = f"{source}->{target}"
        rows = patterns.transition_examples(
            source, target, context=request.context, limit=request.limit
        )
    data = ExamplesData(
        kind=kind,
        subject=subject,
        context=request.context,
        corpus_version=version,
        examples=[
            SongExample(
                song_id=row["song_id"],
                spotify_id=row.get("spotify_id"),
                genre=row.get("genre"),
                decade=row.get("decade"),
                section=row.get("section"),
                section_ordinal=row["ordinal"],
                position=row.get("position"),
                rank=row["rank"],
            )
            for row in rows
        ],
    )
    # An example ID identifies the returned row; no unsupported graph fact is invented.
    return ToolResult[ExamplesData](
        data=data,
        evidence=[
            ToolEvidence(source="corpus", subject=f"example:{item.song_id}")
            for item in data.examples
        ]
        or [ToolEvidence(source="corpus", subject=subject, count=0)],
    )


def color_profile(request: ProgressionInput) -> ToolResult[ColorProfileResponse]:
    data = compute_color_profile(request.progression, request.key)
    return ToolResult[ColorProfileResponse](
        data=data,
        evidence=[ToolEvidence(source="color", subject="deterministic progression profile")],
    )


def format_playback(request: PlaybackInput) -> ToolResult[PlaybackData]:
    analysis = analyze_v2(request.chords, request.key)
    voicings = voice_lead(analysis.chords, request.style)
    data = PlaybackData(
        key=analysis.song_key,
        chords=[
            PlaybackChord(
                symbol=chord.raw_symbol,
                pitch_classes=chord.pitch_classes,
                midi_notes=midi_notes,
            )
            for chord, midi_notes in zip(analysis.chords, voicings, strict=True)
        ],
    )
    return ToolResult[PlaybackData](
        data=data,
        evidence=[ToolEvidence(source="playback", subject="deterministic MIDI voicings")],
    )


class HarmonicTools:
    """Dispatch validated tool calls using request-scoped domain services."""

    def __init__(self, services: ToolServices):
        self.services = services

    @classmethod
    def from_session(cls, session: Session) -> HarmonicTools:
        return cls(ToolServices.from_session(session))

    def call(self, name: str, payload: dict[str, Any]) -> ToolResult[Any]:
        if name not in TOOL_MODELS:
            raise ToolError("unknown_tool", f"Unknown harmonic tool: {name}")
        input_model, output_model = TOOL_MODELS[name]
        try:
            request = input_model.model_validate(payload)
        except ValidationError as exc:
            raise ToolError("invalid_input", str(exc)) from exc
        try:
            handlers = {
                "analyze_progression": lambda: analyze_progression(request),
                "recommend_next": lambda: recommend_next(request, self.services.recommendations),
                "find_substitutes": lambda: find_substitutes(request, self.services.substitutes),
                "generate_progression": lambda: generate_progression(
                    request, self.services.recommendations
                ),
                "explain_transition": lambda: explain_transition(request, self.services.graph),
                "similar_progressions": lambda: similar_progressions(
                    request, self.services.similarity
                ),
                "graph_path": lambda: graph_path(request, self.services.graph),
                "get_examples": lambda: get_examples(
                    request, self.services.patterns, self.services.graph
                ),
                "color_profile": lambda: color_profile(request),
                "format_playback": lambda: format_playback(request),
            }
            result = handlers[name]()
        except ValidationError as exc:
            raise ToolError("invalid_output", str(exc)) from exc
        except ValueError as exc:
            raise ToolError("invalid_input", str(exc)) from exc
        except LookupError as exc:
            raise ToolError("corpus_unavailable", str(exc)) from exc
        except SQLAlchemyError as exc:
            raise ToolError("database_unavailable", "The corpus database is unavailable") from exc
        try:
            return output_model.model_validate(result)
        except ValidationError as exc:
            raise ToolError("invalid_output", str(exc)) from exc
