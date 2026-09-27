"""F70: every exported tool validates schemas and delegates to a domain service."""

from __future__ import annotations

import pytest

from app.ai.schemas import TOOL_MODELS, ToolResult, export_json_schemas
from app.ai.tools import HarmonicTools, ToolError, ToolServices
from app.graph.service import GraphService
from app.services.similarity import SimilarityService
from tests.unit.test_examples_v2_api import ExampleStoreFixture
from tests.unit.test_generate_v2 import _seeded_service
from tests.unit.test_graph_service import FixtureGraph
from tests.unit.test_similarity import FakeStore
from tests.unit.test_substitutes_v2 import _service as substitutes_service


@pytest.fixture
def tools():
    return HarmonicTools(
        ToolServices(
            recommendations=_seeded_service(1),
            substitutes=substitutes_service(),
            similarity=SimilarityService(FakeStore()),
            graph=GraphService(FixtureGraph()),
            patterns=ExampleStoreFixture(),
        )
    )


CASES = [
    ("analyze_progression", {"chords": ["C", "G7", "C"], "key": "C major"}),
    ("recommend_next", {"progression": ["C", "G", "Am"], "key": "C major", "limit": 2}),
    (
        "find_substitutes",
        {"progression": ["C", "F", "G", "C"], "key": "C major", "index": 1},
    ),
    ("generate_progression", {"key": "C major", "length": 3, "k": 1, "start": "C"}),
    ("explain_transition", {"source": "M:I", "target": "M:V"}),
    (
        "similar_progressions",
        {"tokens": ["M:I", "M:V", "M:vi", "M:IV"], "k": 2},
    ),
    ("graph_path", {"source": "M:I", "target": "M:bVI", "k": 2}),
    ("get_examples", {"transition": ["M:V", "M:I"]}),
    ("color_profile", {"progression": ["C", "G", "Am", "F"], "key": "C major"}),
    ("format_playback", {"chords": ["C", "G", "Am"], "key": "C major"}),
]


@pytest.mark.parametrize("name,payload", CASES)
def test_tool_schema_and_invocation(tools, name, payload):
    input_model, output_model = TOOL_MODELS[name]
    assert input_model.model_json_schema()["type"] == "object"
    assert output_model.model_json_schema()["type"] == "object"
    assert input_model.model_validate(payload)
    result = tools.call(name, payload)
    assert isinstance(result, ToolResult)
    assert output_model.model_validate(result.model_dump()) == result
    assert result.evidence
    assert result.fact_ids == sorted(set(result.fact_ids))


def test_export_has_every_tool_and_both_schemas():
    schemas = export_json_schemas()
    assert set(schemas) == {name for name, _ in CASES}
    assert all(set(item) == {"input", "output"} for item in schemas.values())


@pytest.mark.parametrize(
    "name,payload",
    [
        ("analyze_progression", {"chords": ["C", "drop table songs"]}),
        ("recommend_next", {"progression": ["C"], "intent": {"surprise": 99}}),
        ("find_substitutes", {"progression": ["C"], "index": -1}),
        ("generate_progression", {"key": "C major", "length": 99}),
        ("explain_transition", {"source": "../../private", "target": "M:I"}),
        ("similar_progressions", {"tokens": ["M:I", "SQL", "M:V"]}),
        ("graph_path", {"source": "M:I; select 1", "target": "M:V"}),
        ("get_examples", {"transition": ["M:I", "anything"]}),
        ("color_profile", {"progression": ["../../etc/passwd"]}),
        ("format_playback", {"chords": ["C"], "style": "arbitrary"}),
    ],
)
def test_invalid_input_is_typed_and_rejected_before_service(tools, name, payload):
    with pytest.raises(ToolError) as error:
        tools.call(name, payload)
    assert error.value.code == "invalid_input"


def test_graph_evidence_and_direct_service_outputs_match(tools):
    transition = tools.call("explain_transition", {"source": "M:I", "target": "M:V"})
    direct = tools.services.graph.explain_edge("M:I", "M:V")
    assert transition.data.count == direct["evidence"]["count"]
    assert transition.data.edges[0].probability == direct["edges"][0]["prob"]
    assert (
        tools.call("graph_path", {"source": "M:I", "target": "M:bVI"}).data.paths[0].nodes
        == (tools.services.graph.paths("M:I", "M:bVI")[0]["nodes"])
    )


def test_unknown_tool_is_typed(tools):
    with pytest.raises(ToolError) as error:
        tools.call("run_sql", {"query": "select 1"})
    assert error.value.code == "unknown_tool"
