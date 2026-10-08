"""F71 routing, structured output, provenance, retries, and fallback."""

from app.ai.state import AssistantResponse, ParsedIntent
from app.ai.workflow import AssistantWorkflow, heuristic_intent
from tests.unit.test_mcp_server import _tools

ROUTING_QUERIES = [
    ("Recommend the next chord after C G Am in C major", "recommend"),
    ("What comes next after C F G in C major?", "recommend"),
    ("Suggest a chord for Dm G C in C major", "recommend"),
    ("Next chord for Am F C G in C major", "recommend"),
    ("Explain C G Am F in C major", "explain"),
    ("Why does Dm G C work in C major", "explain"),
    ("Explain what a deceptive cadence is", "explain"),
    ("What is a secondary dominant?", "explain"),
    ("Generate a four chord progression in C major", "generate"),
    ("Create a progression in A minor", "generate"),
    ("Make a bright progression", "generate"),
    ("Compose something tense", "generate"),
    ("Find similar progressions to C G Am F", "similar"),
    ("Show neighbors of Dm G C F", "similar"),
    ("What is like this C F G C", "similar"),
    ("Similarity for Am F C G", "similar"),
    ("Compare C G Am F vs C F G C", "compare"),
    ("C Am F G versus C G F C compare", "compare"),
    ("Compare Dm G C vs C F G", "compare"),
    ("Compare C F G C vs Am F C G", "compare"),
]


def test_explanation_prompt_does_not_duplicate_candidate_color_profiles():
    import json

    from app.ai.state import AssistantCandidate

    prompts = []

    def explain(prompt):
        prompts.append(prompt)
        raise ValueError("capture only")

    profile = {"summary": {"brightness": 0.5}, "arc": [{"detail": "x" * 5000}]}
    candidate = AssistantCandidate(
        chords=["C"], color=profile, source_tool="recommend_next", fact_ids=["fact:1"]
    )
    workflow = AssistantWorkflow(_tools(), explanation_model=explain)
    workflow._explain(
        {
            "raw_user_query": "Explain C",
            "route": "recommend",
            "validated_candidates": [candidate],
            "fact_pool": {"fact:1": {}},
            "tool_results": {"color_profile:0": profile},
        }
    )
    context = json.loads(prompts[0].split("Context: ", 1)[1])
    assert "color" not in context["candidates"][0]
    assert context["tool_results"]["color_profile:0"] == profile
    assert candidate.color == profile


def test_prompt_projection_preserves_evidence_and_full_public_result():
    import json

    from app.ai.validators import _symbols

    prompts = []

    def explain(prompt):
        prompts.append(prompt)
        raise ValueError("capture")

    result = AssistantWorkflow(_tools(), explanation_model=explain).run(
        "Recommend a next chord after D A Bm in D major"
    )
    context = json.loads(prompts[0].split("Context: ", 1)[1])
    assert "analysis" not in context
    compact = context["tool_results"]
    assert _symbols(compact) == _symbols(result.tool_results)
    assert compact["analyze_progression"] == result.tool_results["analyze_progression"]
    assert context["facts"] == result.facts
    assert len(json.dumps(compact)) < 0.7 * len(json.dumps(result.tool_results))
    original_axis = result.tool_results["color_profile:0"]["arc"][0]["perceptual"]["warmth"]
    projected_axis = compact["color_profile:0"]["arc"][0]["perceptual"]["warmth"]
    assert "explanation" in original_axis
    assert projected_axis == {
        key: value for key, value in original_axis.items() if key != "explanation"
    }


def test_oversized_explanation_skips_model_and_futile_repair(monkeypatch):
    import app.ai.workflow as module

    monkeypatch.setattr(module, "MAIN_MAX_PROMPT_BYTES", 1)
    calls = []
    result = AssistantWorkflow(_tools(), explanation_model=lambda prompt: calls.append(prompt)).run(
        "Explain D A Bm in D major"
    )
    assert calls == []
    assert result.fallback
    assert "explanation_prompt_too_large" in result.errors


def test_structured_failure_diagnostics_do_not_expose_provider_content():
    from types import SimpleNamespace

    from app.ai.workflow import StructuredOutputError

    for reason, code in (
        ("max_tokens", "output_limit"),
        ("private provider text", "structured_parse"),
    ):
        exc = StructuredOutputError(SimpleNamespace(response_metadata={"stop_reason": reason}))
        assert str(exc) == code
        assert exc.code == code


def test_provider_parse_failure_preserves_usage_and_reports_token_limit(monkeypatch):
    from types import SimpleNamespace

    import langchain_anthropic
    import pytest

    from app.ai.usage import UsageMeter
    from app.ai.workflow import StructuredOutputError, _llm_calls

    class Model:
        def __init__(self, **kwargs):
            pass

        def with_structured_output(self, schema, *, include_raw, method):
            return self

        def invoke(self, prompt):
            return {
                "raw": SimpleNamespace(
                    usage_metadata={"input_tokens": 10, "output_tokens": 1024},
                    response_metadata={"stop_reason": "max_tokens"},
                ),
                "parsed": None,
                "parsing_error": ValueError("private provider text"),
            }

    monkeypatch.setenv("ANTHROPIC_API_KEY", "unit-test-placeholder")
    monkeypatch.setattr(langchain_anthropic, "ChatAnthropic", Model)
    meter = UsageMeter()
    _, main = _llm_calls(meter)
    with pytest.raises(StructuredOutputError, match="^output_limit$"):
        main("prompt")
    assert meter.tokens_in == 10
    assert meter.tokens_out == 1024
    assert meter.cost_usd > 0


def test_real_tool_parser_failure_codes_are_sanitized():
    from langchain_core.messages import AIMessage
    from langchain_core.output_parsers.openai_tools import PydanticToolsParser
    from langchain_core.outputs import ChatGeneration

    from app.ai.state import ExplanationDraft
    from app.ai.workflow import StructuredOutputError

    parser = PydanticToolsParser(tools=[ExplanationDraft], first_tool_only=True)
    for args, expected in (
        ({"claims": [{"text": "safe"}]}, "claims.fact_ids:missing"),
        ({"claims": [{"text": "safe", "fact_ids": []}]}, "claims.fact_ids:too_short"),
        ({"claims": [{"text": "x" * 501, "fact_ids": ["f"]}]}, "claims.text:string_too_long"),
        ({"claims": ["private generated content"]}, "claims:model_type"),
        (
            {"claims": [{"text": "safe", "fact_ids": ["f"], "private field": "secret"}]},
            "structured_parse",
        ),
    ):
        raw = AIMessage(
            content="", tool_calls=[{"name": "ExplanationDraft", "args": args, "id": "test"}]
        )
        try:
            parser.parse_result([ChatGeneration(message=raw)])
        except Exception as exc:
            code = StructuredOutputError(raw, exc).code
        else:
            raise AssertionError("Malformed provider payload unexpectedly parsed")
        assert expected in code
        assert "private" not in code and "secret" not in code and "xxxxx" not in code
    empty = AIMessage(content="private prose")
    assert parser.parse_result([ChatGeneration(message=empty)]) is None
    assert StructuredOutputError(empty, missing=True).code == "missing_structured_output"
    assert StructuredOutputError(empty, KeyError("private tool")).code == "structured_parse"
    unknown = AIMessage(content="", tool_calls=[{"name": "private tool", "args": {}, "id": "test"}])
    try:
        parser.parse_result([ChatGeneration(message=unknown)])
    except Exception as exc:
        assert StructuredOutputError(unknown, exc).code == "output_parse"
    else:
        raise AssertionError("Unknown tool unexpectedly parsed")


def test_native_explanation_schema_reaches_provider_and_keeps_local_validation(monkeypatch):
    import importlib
    import json

    import langchain_anthropic.chat_models as adapter
    import pytest
    from anthropic import DefaultHttpxClient

    from app.ai.usage import UsageMeter
    from app.ai.workflow import StructuredOutputError, _llm_calls

    # Use the installed SDK's transport generation (httpx or httpx2).
    transport_module = next(
        base.__module__.split(".")[0]
        for base in DefaultHttpxClient.__mro__
        if base.__module__.split(".")[0] in {"httpx", "httpx2"}
    )
    httpx = importlib.import_module(transport_module)
    requests = []

    def respond(request):
        body = json.loads(request.content)
        requests.append(body)
        text = "A supported transition." if len(requests) == 1 else "x" * 501
        return httpx.Response(
            200,
            json={
                "id": "msg_test",
                "type": "message",
                "role": "assistant",
                "model": body["model"],
                "stop_reason": "end_turn",
                "stop_sequence": None,
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            {
                                "claims": [
                                    {"text": text, "fact_ids": ["fact:1"], "theory_labels": []}
                                ]
                            }
                        ),
                    }
                ],
                "usage": {"input_tokens": 10, "output_tokens": 20},
            },
        )

    monkeypatch.setenv("ANTHROPIC_API_KEY", "unit-test-placeholder")
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        monkeypatch.setattr(adapter, "_get_default_httpx_client", lambda **kwargs: client)
        meter = UsageMeter()
        _, main = _llm_calls(meter)
        draft = main("Explain the supplied evidence")
        assert draft.claims[0].fact_ids == ["fact:1"]
        schema = requests[0]["output_config"]["format"]
        assert schema["type"] == "json_schema"
        assert schema["schema"]["properties"]["claims"]["type"] == "array"
        assert schema["schema"]["additionalProperties"] is False
        assert "tools" not in requests[0]
        assert requests[0]["max_tokens"] == 1024
        # Provider schema transformations omit some length constraints; local
        # Pydantic validation must continue to enforce the unchanged limit.
        with pytest.raises(StructuredOutputError):
            main("Explain the supplied evidence")
        assert meter.tokens_in == 20 and meter.tokens_out == 40
        assert meter.cost_usd > 0


def test_twenty_query_routing_suite_and_valid_outputs():
    tools = _tools()
    workflow = AssistantWorkflow(tools)
    results = [(query, expected, workflow.run(query)) for query, expected in ROUTING_QUERIES]
    assert sum(result.route == expected for _, expected, result in results) >= 18
    for _, _, result in results:
        assert AssistantResponse.model_validate(result.model_dump(mode="json"))
        assert set(result.fact_ids) == set(result.facts)
        assert all(set(claim.fact_ids) <= set(result.facts) for claim in result.claims)
        assert all(candidate.explanation for candidate in result.candidates)
        assert all(
            set(candidate.chords)
            <= {
                item["symbol"]
                for item in result.tool_results.get("analyze_progression", {}).get("chords", [])
            }
            | {
                item["raw_symbol"]
                for item in result.tool_results.get("analyze_progression", {}).get("chords", [])
            }
            | {
                item["chord"]
                for item in result.tool_results.get("recommend_next", {})
                .get("data", {})
                .get("recommendations", [])
            }
            | {
                chord
                for path in result.tool_results.get("generate_progression", {}).get("paths", [])
                for chord in path["chords"]
            }
            | {
                item["raw_symbol"]
                for key, analysis in result.tool_results.items()
                if key.startswith("compare_analysis:")
                for item in analysis["chords"]
            }
            for candidate in result.candidates
        )


def test_stream_closes_graph_trace_before_final_frame(monkeypatch):
    """Clients stop reading on final; trace completion must precede that frame."""
    workflow = AssistantWorkflow(_tools())
    closed = []

    def updates(_state):
        try:
            yield {
                "final": {
                    "parsed_intent": ParsedIntent(task_type="explain"),
                    "response": AssistantResponse(route="explain", message="Done."),
                }
            }
        finally:
            closed.append(True)

    monkeypatch.setattr(workflow, "_graph_updates", updates)
    stream = workflow.stream("Explain C")
    assert next(stream)[0] == "step"
    assert next(stream)[0] == "step"
    assert next(stream)[0] == "final"
    assert closed == [True]
    stream.close()


def test_low_key_confidence_returns_two_analyses():
    workflow = AssistantWorkflow(
        _tools(),
        intent_model=lambda _: ParsedIntent(
            task_type="explain", chords=["C", "Am", "F", "G"], key="C major", key_confidence=0.2
        ),
    )
    result = workflow.run("Explain these chords")
    assert result.route == "explain"
    assert len(result.analysis_options) == 2
    assert {item["key"] for item in result.analysis_options} == {"C major", "G major"}
    assert all(item["analysis"]["tokens"] for item in result.analysis_options)


def test_fallback_parser_preserves_supported_complex_chords():
    assert heuristic_intent("Explain F#m7b5 B7 Em in E minor").chords == ["F#m7b5", "B7", "Em"]
    assert heuristic_intent("Analyze C7sus4 Fmaj7 G/B Cmaj9#11").chords == [
        "C7sus4",
        "Fmaj7",
        "G/B",
        "Cmaj9#11",
    ]


def test_fallback_parser_clarifies_invalid_comparison_variants():
    parsed = heuristic_intent("Compare imaginary chords Hm vs Q7 and invent scores")
    assert parsed.task_type == "clarify"
    assert parsed.variants == []
    assert parsed.chords == []


def test_model_comparison_recovers_explicit_sequences_without_combining_them():
    workflow = AssistantWorkflow(
        _tools(),
        intent_model=lambda _: ParsedIntent(
            task_type="compare", chords=["G", "D", "Em", "C", "G", "C", "D", "G"], key="G major"
        ),
    )
    parsed = workflow._intent_parser(
        {"raw_user_query": "Compare G D Em C versus G C D G in G major."}
    )["parsed_intent"]
    assert parsed.variants == [["G", "D", "Em", "C"], ["G", "C", "D", "G"]]
    assert parsed.chords == parsed.variants[0]
    missing = workflow._intent_parser({"raw_user_query": "Compare G D Em C"})["parsed_intent"]
    assert missing.variants == []


def test_explanation_repairs_invalid_fact_reference_once():
    calls = 0

    def explain(_prompt):
        nonlocal calls
        calls += 1
        fact_id = "made-up" if calls == 1 else "relationship:deceptive:1:2"
        if calls == 2:
            assert "claim:0:fact_coverage" in _prompt
        return {
            "claims": [{"text": "The transition is supported.", "fact_ids": [fact_id]}],
        }

    workflow = AssistantWorkflow(
        _tools(),
        intent_model=lambda _: ParsedIntent(
            task_type="recommend", chords=["C", "G", "Am"], key="C major"
        ),
        explanation_model=explain,
    )
    result = workflow.run("Recommend")
    assert calls == 2
    assert not result.fallback
    assert all(set(claim.fact_ids) <= set(result.fact_ids) for claim in result.claims)


def test_invented_chord_rejected_then_deterministic_fallback():
    calls = 0

    def explain(_prompt):
        nonlocal calls
        calls += 1
        return {
            "claims": [
                {
                    "text": "Add F#7 for a dramatic turn.",
                    "fact_ids": ["relationship:deceptive:1:2"],
                }
            ]
        }

    workflow = AssistantWorkflow(
        _tools(),
        intent_model=lambda _: ParsedIntent(
            task_type="recommend", chords=["C", "G", "Am"], key="C major"
        ),
        explanation_model=explain,
    )
    result = workflow.run("Recommend")
    assert calls == 2
    assert result.fallback
    assert "F#7" not in result.message
    assert any("claim:0:chord_provenance" in code for code in result.errors)


def test_invalid_explanation_schema_gets_one_repair():
    calls = 0

    def explain(_prompt):
        nonlocal calls
        calls += 1
        return (
            {}
            if calls == 1
            else {
                "claims": [
                    {
                        "text": "The transition is supported.",
                        "fact_ids": ["relationship:deceptive:1:2"],
                    }
                ]
            }
        )

    result = AssistantWorkflow(
        _tools(),
        intent_model=lambda _: ParsedIntent(task_type="recommend", chords=["C", "G", "Am"]),
        explanation_model=explain,
    ).run("Recommend C G Am")
    assert calls == 2
    assert not result.fallback
    assert AssistantResponse.model_validate(result.model_dump(mode="json"))


def test_uncited_model_message_is_rejected_and_article_a_is_not_a_chord():
    fact_id = "relationship:deceptive:1:2"

    def intent(_prompt):
        return ParsedIntent(task_type="recommend", chords=["C", "G", "Am"])

    valid = AssistantWorkflow(
        _tools(),
        intent_model=intent,
        explanation_model=lambda _: {
            "claims": [{"text": "A gentle transition is supported.", "fact_ids": [fact_id]}]
        },
    ).run("Recommend C G Am")
    assert not valid.fallback
    assert valid.message == valid.claims[0].text

    invalid = AssistantWorkflow(
        _tools(),
        intent_model=intent,
        explanation_model=lambda _: {
            "message": "The Beatles used this exact progression in Let It Be.",
            "claims": [{"text": "A transition occurs.", "fact_ids": [fact_id]}],
        },
    ).run("Recommend C G Am")
    assert invalid.fallback
    assert "Beatles" not in invalid.message


def test_explain_model_receives_validated_graph_evidence():
    prompts = []

    def explain(prompt):
        prompts.append(prompt)
        return {
            "claims": [
                {
                    "text": "The cadence resolves toward the tonic.",
                    "fact_ids": ["relationship:authentic:1:2"],
                }
            ]
        }

    result = AssistantWorkflow(
        _tools(),
        intent_model=lambda _: ParsedIntent(task_type="explain", chords=["C", "G", "C"]),
        explanation_model=explain,
    ).run("Explain C G C")
    assert not result.fallback
    assert "explain_transition" in result.tool_results
    assert '"tool_results"' in prompts[0]
    assert '"edges"' in prompts[0]


def test_export_uses_playback_tool_and_invalid_chord_clarifies():
    workflow = AssistantWorkflow(
        _tools(),
        intent_model=lambda _: ParsedIntent(
            task_type="recommend", chords=["C", "G", "Am"], key="C major", export=True
        ),
    )
    result = workflow.run("Recommend and export")
    assert result.playback and result.playback["chords"]

    invalid = AssistantWorkflow(
        _tools(),
        intent_model=lambda _: ParsedIntent(task_type="recommend", chords=["drop table songs"]),
    ).run("malformed chords")
    assert invalid.route == "clarify"
    assert "analyze:invalid_input" in invalid.errors


def test_playable_request_recovers_missed_model_export_flag():
    query = "Generate a progression in D minor and make it playable."
    assert heuristic_intent(query).export is True
    assert heuristic_intent("Generate a playful progression in D minor.").export is False
    assert (
        heuristic_intent("Generate a progression in D minor, but do not play it.").export is False
    )
    assert heuristic_intent("Generate a progression in D minor without MIDI.").export is False
    assert heuristic_intent("Explain what 'play' means here.").export is False
    workflow = AssistantWorkflow(
        _tools(),
        intent_model=lambda _: ParsedIntent(task_type="generate", key="D minor", export=False),
    )
    result = workflow.run(query)
    assert result.route == "generate"
    assert result.candidates
    assert result.playback and result.playback["chords"]
    no_play = workflow.run("Generate a progression in D minor, but do not play it.")
    assert no_play.route == "generate"
    assert no_play.playback is None


def test_provider_failure_uses_deterministic_route_and_explanation():
    calls = 0

    def unavailable(_prompt):
        nonlocal calls
        calls += 1
        raise TimeoutError("provider did not respond")

    result = AssistantWorkflow(
        _tools(), intent_model=unavailable, explanation_model=unavailable
    ).run("Recommend the next chord after C G Am in C major")
    assert result.route == "recommend"
    assert result.fallback
    assert "intent_model_failed:TimeoutError" in result.errors
    assert calls == 2  # one intent attempt, then immediate explanation fallback


def test_explanation_failure_retains_analyzer_citations_and_registered_relationships():
    from app.ai.validators import validate_claims

    def unavailable(_):
        raise TimeoutError("provider unavailable")

    result = AssistantWorkflow(
        _tools(),
        intent_model=lambda _: ParsedIntent(task_type="explain", chords=["G", "Am"], key="C major"),
        explanation_model=unavailable,
    ).run("Explain this transition")
    assert result.fallback  # Never represent a deterministic fallback as model success.
    assert result.claims
    assert "deceptive" in {label for claim in result.claims for label in claim.theory_labels}
    assert validate_claims(result.claims, result.facts, result.tool_results) == []
    assert all(set(claim.fact_ids) <= set(result.facts) for claim in result.claims)


def test_modulating_similarity_and_generation_use_opening_context():
    from app.ai.tools import ToolError

    calls = []

    class CapturingTools:
        def call(self, name, arguments):
            calls.append((name, arguments))
            raise ToolError("test_capture", "Captured")

    chords = ["C", "F", "G", "C"] * 2 + ["Am", "Dm", "E", "Am"] * 2
    workflow = AssistantWorkflow(CapturingTools())
    for route in ("similar", "generate"):
        workflow._retrieve(
            {
                "parsed_intent": ParsedIntent(task_type=route, chords=chords),
                "route": route,
                "analysis": {"data": {"key_regions": [{"key": "C major"}, {"key": "A minor"}]}},
            }
        )
    assert calls[0][1]["progression"] == chords[:8]
    assert calls[0][1]["key"] is None
    assert calls[1][1]["start"] == "C"
    assert calls[1][1]["key"] == "C major"
