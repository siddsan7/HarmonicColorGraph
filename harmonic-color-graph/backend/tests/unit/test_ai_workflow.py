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


def test_twenty_query_routing_suite_and_valid_outputs():
    tools = _tools()
    workflow = AssistantWorkflow(tools)
    results = [(query, expected, workflow.run(query)) for query, expected in ROUTING_QUERIES]
    assert sum(result.route == expected for _, expected, result in results) >= 18
    for _, _, result in results:
        assert AssistantResponse.model_validate(result.model_dump(mode="json"))
        assert set(result.fact_ids) == set(result.facts)
        assert all(set(claim.fact_ids) <= set(result.facts) for claim in result.claims)
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


def test_explanation_repairs_invalid_fact_reference_once():
    calls = 0

    def explain(_prompt):
        nonlocal calls
        calls += 1
        fact_id = "made-up" if calls == 1 else "relationship:deceptive:1:2"
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
