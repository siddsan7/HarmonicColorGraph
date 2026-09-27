"""F70.5: MCP discovery and invocation over request-scoped harmonic services."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from functools import lru_cache
from typing import Any

import anyio
from mcp.server import Server, ServerRequestContext
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolRequestParams,
    CallToolResult,
    ListToolsResult,
    PaginatedRequestParams,
    TextContent,
    Tool,
)
from sqlalchemy.orm import Session, sessionmaker

from app.ai.schemas import TOOL_MODELS
from app.ai.tools import HarmonicTools, ToolError
from app.db.session import create_session_factory

ToolProvider = Callable[[], AbstractContextManager[HarmonicTools]]

DESCRIPTIONS = {
    "analyze_progression": "Analyze chord symbols, keys, Roman functions, and relationships.",
    "recommend_next": "Rank corpus-backed next chords for a progression and musical intent.",
    "find_substitutes": "Find contextual replacement chords at one progression position.",
    "generate_progression": "Generate constrained, playable chord progressions.",
    "explain_transition": "Read a graph transition and its recorded evidence.",
    "similar_progressions": "Find structural or surface neighbors of a progression.",
    "graph_path": "Find bounded paths between harmonic function nodes.",
    "get_examples": "Retrieve exact corpus examples for a pattern or transition.",
    "color_profile": "Compute a deterministic progression color profile.",
    "format_playback": "Turn chord symbols into deterministic MIDI voicings.",
}


@lru_cache
def _session_factory() -> sessionmaker[Session]:
    # The engine is created on the first call, never during server import.
    return create_session_factory()


@contextmanager
def _default_tools() -> Iterator[HarmonicTools]:
    with _session_factory()() as session:
        yield HarmonicTools.from_session(session)


def _tool_definitions() -> list[Tool]:
    return [
        Tool(
            name=name,
            description=DESCRIPTIONS[name],
            inputSchema=input_model.model_json_schema(),
            outputSchema=output_model.model_json_schema(),
        )
        for name, (input_model, output_model) in TOOL_MODELS.items()
    ]


def create_server(tool_provider: ToolProvider = _default_tools) -> Server[Any]:
    """Build a server; tests inject the same tool layer with fixture services."""

    async def list_tools(
        _ctx: ServerRequestContext, _params: PaginatedRequestParams | None
    ) -> ListToolsResult:
        return ListToolsResult(tools=_tool_definitions())

    async def call_tool(
        _ctx: ServerRequestContext, params: CallToolRequestParams
    ) -> CallToolResult:
        def invoke() -> dict[str, Any]:
            with tool_provider() as tools:
                return tools.call(params.name, params.arguments or {}).model_dump(mode="json")

        try:
            payload = await anyio.to_thread.run_sync(invoke)
        except ToolError as exc:
            error = {"error": {"code": exc.code, "message": str(exc)}}
            return CallToolResult(
                content=[TextContent(type="text", text=json.dumps(error, ensure_ascii=False))],
                isError=True,
            )
        return CallToolResult(
            content=[TextContent(type="text", text=json.dumps(payload, ensure_ascii=False))],
            structuredContent=payload,
        )

    return Server(
        "Harmonic Color Graph",
        version="0.1.0",
        instructions="Use harmonic tools for evidence. Cite only returned fact IDs.",
        on_list_tools=list_tools,
        on_call_tool=call_tool,
    )


server = create_server()
app = server.streamable_http_app(stateless_http=True, json_response=True)


async def _run_stdio() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(_run_stdio())
