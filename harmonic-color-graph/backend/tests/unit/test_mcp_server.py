"""F70.5 MCP discovery and direct-service parity over an in-process client."""

import asyncio
import json
import sys
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path

import httpx2
from mcp import Client, StdioServerParameters
from mcp.client.streamable_http import streamable_http_client

from app.ai.schemas import TOOL_MODELS
from app.ai.tools import HarmonicTools, ToolServices
from app.graph.service import GraphService
from app.mcp.server import create_server
from app.services.similarity import SimilarityService
from tests.unit.test_examples_v2_api import ExampleStoreFixture
from tests.unit.test_generate_v2 import _seeded_service
from tests.unit.test_graph_service import FixtureGraph
from tests.unit.test_similarity import FakeStore
from tests.unit.test_substitutes_v2 import _service as substitutes_service


def _tools() -> HarmonicTools:
    return HarmonicTools(
        ToolServices(
            recommendations=_seeded_service(1),
            substitutes=substitutes_service(),
            similarity=SimilarityService(FakeStore()),
            graph=GraphService(FixtureGraph()),
            patterns=ExampleStoreFixture(),
        )
    )


def _without_timing(name: str, payload: dict) -> dict:
    payload = deepcopy(payload)
    if name == "recommend_next":
        payload["data"]["meta"].pop("latency_ms")
    if name == "generate_progression":
        payload["data"].pop("latency_ms")
    return payload


def test_discovery_and_all_tool_round_trips_match_direct_calls():
    direct = _tools()

    @contextmanager
    def provider():
        yield direct

    cases = [
        ("analyze_progression", {"chords": ["C", "G", "C"], "key": "C major"}),
        ("recommend_next", {"progression": ["C", "G", "Am"], "key": "C major", "limit": 2}),
        (
            "find_substitutes",
            {"progression": ["C", "F", "G", "C"], "key": "C major", "index": 1},
        ),
        ("generate_progression", {"key": "C major", "length": 3, "k": 1, "start": "C"}),
        ("explain_transition", {"source": "M:I", "target": "M:V"}),
        ("similar_progressions", {"tokens": ["M:I", "M:V", "M:vi", "M:IV"]}),
        ("color_profile", {"progression": ["C", "G", "Am"], "key": "C major"}),
        ("graph_path", {"source": "M:I", "target": "M:bVI"}),
        ("get_examples", {"transition": ["M:V", "M:I"]}),
        ("format_playback", {"chords": ["C", "G", "Am"], "key": "C major"}),
    ]

    async def exercise():
        async with Client(create_server(provider)) as client:
            discovered = {tool.name: tool for tool in (await client.list_tools()).tools}
            assert set(discovered) == set(TOOL_MODELS)
            for name, (input_model, output_model) in TOOL_MODELS.items():
                assert discovered[name].input_schema == input_model.model_json_schema()
                assert discovered[name].output_schema == output_model.model_json_schema()
            for name, arguments in cases:
                result = await client.call_tool(name, arguments)
                assert not result.is_error
                expected = direct.call(name, arguments).model_dump(mode="json")
                assert json.loads(result.content[0].text) == result.structured_content
                assert _without_timing(name, result.structured_content) == _without_timing(
                    name, expected
                )
                assert TOOL_MODELS[name][1].model_validate(result.structured_content)

    asyncio.run(exercise())


def test_invalid_harmonic_input_returns_typed_mcp_tool_error():
    @contextmanager
    def provider():
        yield _tools()

    async def exercise():
        async with Client(create_server(provider)) as client:
            for name, arguments in (
                ("analyze_progression", {"chords": ["drop table songs"]}),
                ("graph_path", {"source": "../../etc/passwd", "target": "M:I"}),
                ("get_examples", {"transition": ["M:I", "unvalidated"]}),
            ):
                result = await client.call_tool(name, arguments)
                assert result.is_error
                assert json.loads(result.content[0].text)["error"]["code"] == "invalid_input"
                assert result.structured_content is None

    asyncio.run(exercise())


def test_stdio_client_discovers_and_calls_pure_tool():
    backend = Path(__file__).resolve().parents[2]
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-m", "app.mcp.server"],
        cwd=backend,
    )

    async def exercise():
        async with Client(parameters, read_timeout_seconds=15) as client:
            assert "analyze_progression" in {
                item.name for item in (await client.list_tools()).tools
            }
            result = await client.call_tool(
                "analyze_progression", {"chords": ["C", "G", "C"], "key": "C major"}
            )
            assert not result.is_error
            assert result.structured_content["data"]["song_key"] == "C major"

    asyncio.run(exercise())


def test_streamable_http_asgi_client_round_trip():
    @contextmanager
    def provider():
        yield _tools()

    app = create_server(provider).streamable_http_app(stateless_http=True, json_response=True)

    async def exercise():
        async with app.router.lifespan_context(app):
            async with httpx2.AsyncClient(
                transport=httpx2.ASGITransport(app=app), base_url="http://127.0.0.1:8001"
            ) as http_client:
                transport = streamable_http_client(
                    "http://127.0.0.1:8001/mcp", http_client=http_client
                )
                async with Client(transport) as client:
                    result = await client.call_tool("analyze_progression", {"chords": ["C", "G"]})
                    assert not result.is_error
                    assert result.structured_content["data"]["tokens"]

    asyncio.run(exercise())
