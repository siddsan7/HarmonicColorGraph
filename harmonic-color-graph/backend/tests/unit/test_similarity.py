"""F51 ranking contracts without requiring a live vector database."""

from app.schemas.similar_v2 import (
    SimilarChordRequest,
    SimilarFunctionRequest,
    SimilarProgressionRequest,
)
from app.services.similarity import SimilarityService, _parse_tokens, _rotation_of


class FakeStore:
    def active_version(self):
        return "cv-test"

    def default_model(self):
        return "chord2vec"

    def vector(self, kind, subject, *, model):
        if kind == "pattern":
            return [1.0] + [0.0] * 63
        return [1.0] + [0.0] * 63 if subject in {"M:I", "M:V", "M:vi", "M:IV"} else None

    def neighbors(self, kind, subject, *, model, limit):
        return [{"subject_id": "M:V7", "similarity": 0.83}]

    def neighbors_by_vector(self, kind, vector, *, model, limit, exclude):
        return [
            {"subject_id": "M:vi M:IV M:I M:V", "similarity": 0.99},
            {"subject_id": "M:I M:V M:IV M:vi", "similarity": 0.85},
        ]

    def pattern_metadata(self, ids):
        return {
            item: {"subject_id": item, "support": 100, "context_lifts": {"genre:pop": 1.4}}
            for item in ids
        }

    def popular_patterns(self):
        return list(self.pattern_metadata(["M:vi M:IV M:I M:V", "M:I M:V M:IV M:vi"]).values())

    def pattern_colors(self, ids, axis):
        return {item: 0.7 for item in ids}

    def chord_candidates(self, chord):
        return [
            {"chord": "C:maj", "token": "M:I", "count": 10},
            {"chord": "C:maj", "token": "M:IV", "count": 2},
            {"chord": "C:maj7", "token": "M:I", "count": 8},
            {"chord": "G:maj", "token": "M:V", "count": 9},
        ]


def test_function_neighbors_use_requested_model():
    response = SimilarityService(FakeStore()).functions(
        SimilarFunctionRequest(token="M:V", model="fastrp", k=3)
    )
    assert response.model == "fastrp"
    assert response.results[0].subject_id == "M:V7"


def test_chord_similarity_blends_pitch_and_usage():
    response = SimilarityService(FakeStore()).chords(SimilarChordRequest(chord="C", k=2))
    assert response.results[0].subject_id == "C:maj7"
    assert response.results[0].similarity > response.results[1].similarity


def test_progression_rotations_are_flagged():
    request = SimilarProgressionRequest(tokens=["I", "V", "vi", "IV"])
    response = SimilarityService(FakeStore()).progressions(request)
    assert response.query == "M:I M:V M:vi M:IV"
    assert response.results[0].rotation_of == response.query
    assert response.results[1].rotation_of is None
    assert _rotation_of(["M:I", "M:V", "M:vi", "M:IV"], ["M:vi", "M:IV", "M:I", "M:V"])


def test_surface_mode_uses_token_overlap_and_color_filter():
    request = SimilarProgressionRequest.model_validate(
        {
            "progression": "I V vi IV",
            "mode": "surface",
            "filters": {"genre": "pop", "color": {"axis": "brightness", "min": 0.6}},
        }
    )
    response = SimilarityService(FakeStore()).progressions(request)
    assert response.model == "token_overlap"
    assert len(response.results) == 2
    assert response.results[0].similarity == 1.0
    assert _parse_tokens(request) == ["M:I", "M:V", "M:vi", "M:IV"]
