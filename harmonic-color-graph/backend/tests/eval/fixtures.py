"""Small, versioned in-memory tool corpus shipped with the F76 evaluation CLI."""

from __future__ import annotations

from app.ai.tools import HarmonicTools, ToolServices
from app.graph.service import GraphService
from app.predict.ngram import InMemoryNgramStore, KNPredictor
from app.recommend.substitutes import SubstitutionService
from app.services.recommend import RecommendationService
from app.services.similarity import SimilarityService


class _Examples:
    def transition_examples_many(self, pairs, *, limit):
        return {pair: [] for pair in pairs}


class _Facts:
    def existing_ids(self, fact_ids):
        return set()


class _Vectors:
    def active_version(self):
        return "ai-eval-v1"

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
            {"chord": "C:maj7", "token": "M:I", "count": 8},
            {"chord": "G:maj", "token": "M:V", "count": 9},
        ]


class _Graph:
    def __init__(self):
        self.nodes = {
            f"function:{token}": {"id": f"function:{token}", "props": {"chromaticity": value}}
            for token, value in (("M:I", 0), ("M:V", 0), ("M:iv", 1), ("M:bVI", 2))
        }
        self.edges = [
            self._edge("M:I", "M:V", 0.8),
            self._edge("M:V", "M:bVI", 0.6),
            self._edge("M:I", "M:iv", 0.5),
            self._edge("M:iv", "M:bVI", 0.5),
        ]

    @staticmethod
    def _edge(source, target, probability):
        return {
            "src": f"function:{source}",
            "dst": f"function:{target}",
            "type": "TRANSITIONS_TO",
            "context_id": 0,
            "prob": probability,
            "props": {},
        }

    def active_version(self):
        return "ai-eval-v1"

    def node(self, node_id):
        return self.nodes.get(node_id)

    def context_by_key(self, context):
        return {"id": 0} if context == "global" else None

    def outgoing_edges(self, src, *, edge_type=None, context_id=None):
        return [
            edge
            for edge in self.edges
            if edge["src"] == src
            and (edge_type is None or edge["type"] == edge_type)
            and (context_id is None or edge["context_id"] == context_id)
        ]

    def function_adjacency(self, context_id):
        return [edge for edge in self.edges if edge["context_id"] == context_id]

    def edges_between(self, src, dst, *, context_id=None):
        return [
            edge
            for edge in self.edges
            if edge["src"] == src
            and edge["dst"] == dst
            and (context_id is None or edge["context_id"] == context_id)
        ]


class _Patterns:
    def active_version(self):
        return "ai-eval-v1"

    def examples(self, pattern, *, context, limit):
        return []

    def transition_examples(self, from_token, to_token, *, context, limit):
        return []


def seeded_tools() -> HarmonicTools:
    counts = {"M:I": 60, "M:ii": 24, "M:IV": 48, "M:V": 53, "M:V7": 21, "M:vi": 37}
    ngrams = InMemoryNgramStore(version="ai-eval-v1")
    ngrams.add_row(
        "global",
        1,
        "",
        total=sum(counts.values()),
        distinct_next=len(counts),
        next=counts,
        cont=counts,
    )
    predictor = KNPredictor(ngrams)
    return HarmonicTools(
        ToolServices(
            recommendations=RecommendationService(predictor, _Examples(), _Facts()),
            substitutes=SubstitutionService(predictor, lambda history, key, prediction: []),
            similarity=SimilarityService(_Vectors()),
            graph=GraphService(_Graph()),
            patterns=_Patterns(),
        )
    )
