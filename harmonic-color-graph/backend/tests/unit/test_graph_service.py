"""F25 graph traversal behavior on a deterministic fixture."""

from app.graph.service import GraphService


class FixtureGraph:
    def __init__(self):
        self.nodes = {
            "function:M:I": {"id": "function:M:I", "props": {"chromaticity": 0}},
            "function:M:V": {"id": "function:M:V", "props": {"chromaticity": 0}},
            "function:M:iv": {"id": "function:M:iv", "props": {"chromaticity": 1}},
            "function:M:bVI": {"id": "function:M:bVI", "props": {"chromaticity": 2}},
        }
        self.edges = [
            self.edge("M:I", "M:V", 0.8),
            self.edge("M:V", "M:bVI", 0.6),
            self.edge("M:I", "M:iv", 0.5),
            self.edge("M:iv", "M:bVI", 0.5),
            self.edge("M:bVI", "M:I", 0.7),
        ]

    @staticmethod
    def edge(src, dst, prob):
        return {
            "src": f"function:{src}",
            "dst": f"function:{dst}",
            "type": "TRANSITIONS_TO",
            "context_id": 0,
            "prob": prob,
            "props": {},
        }

    def active_version(self):
        return "fixture-a"

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


def test_neighborhood_orders_by_probability_and_respects_limit():
    result = GraphService(FixtureGraph()).neighborhood("M:I", limit=1)
    assert result["edges"][0]["dst"] == "function:M:V"
    assert len(result["edges"]) == 1
    assert {node["id"] for node in result["nodes"]} == {"function:M:I", "function:M:V"}


def test_best_first_paths_and_chromaticity_constraint():
    service = GraphService(FixtureGraph())
    paths = service.paths("M:I", "M:bVI", k=2, constraint="increasing_chromaticity")
    assert [path["nodes"] for path in paths] == [
        ["function:M:I", "function:M:V", "function:M:bVI"],
        ["function:M:I", "function:M:iv", "function:M:bVI"],
    ]
    assert service.paths("M:bVI", "M:I", constraint="increasing_chromaticity") == []


def test_unknown_context_fails_before_query():
    service = GraphService(FixtureGraph())
    try:
        service.neighborhood("M:I", context="genre:missing")
    except ValueError as exc:
        assert "Unknown graph context" in str(exc)
    else:
        raise AssertionError("Unknown context should fail")


def test_graph_api_path_contract_and_typed_error():
    from fastapi.testclient import TestClient

    from app.api.graph_v2 import _graph_cache, graph_service
    from app.main import app

    app.dependency_overrides[graph_service] = lambda: GraphService(FixtureGraph())
    try:
        client = TestClient(app)
        response = client.post(
            "/v2/graph/path",
            json={"from": "M:I", "to": "M:bVI", "constraint": "increasing_chromaticity"},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["meta"]["corpus_version"] == "fixture-a"
        assert payload["data"]["paths"][0]["nodes"][-1] == "function:M:bVI"
        hits_before = _graph_cache().metrics.l1_hits
        assert (
            client.post(
                "/v2/graph/path",
                json={"from": "M:I", "to": "M:bVI", "constraint": "increasing_chromaticity"},
            ).json()
            == payload
        )
        assert _graph_cache().metrics.l1_hits == hits_before + 1

        missing = client.get("/v2/graph/neighborhood", params={"id": "M:I", "context": "bad"})
        assert missing.status_code == 422
        assert missing.json()["error"]["code"] == "invalid_context"
    finally:
        app.dependency_overrides.clear()
