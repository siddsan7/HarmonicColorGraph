"""Frozen bounded selection, public limit prefixes and downstream score order."""

from dataclasses import replace
from math import exp

import pytest
from fastapi.testclient import TestClient

from app.ai.state import AssistantCandidate
from app.ai.workflow import AssistantWorkflow
from app.api.recommend_v2 import recommendation_service
from app.main import app
from app.recommend.scorer import ScoredCandidate
from app.recommend.selection import select_bounded_intent, select_strong_adjacent
from tests.eval.adjacent_ranking_experiment import rerank
from tests.unit.test_pareto_experiment import ranked
from tests.unit.test_recommend_v2_api import _service


def test_score_exchange_preserves_components_and_utility_distribution():
    rows = [
        replace(row, score_breakdown={"intent": row.score, "total": row.score}) for row in ranked()
    ]
    result = select_strong_adjacent(rows, {"darker_brighter": 0.7})
    assert [r.token for r in result] == [r.token for r in rerank(rows, {"darker_brighter": 0.7})]
    assert [r.score for r in result] == [r.score for r in rows]
    assert sum(exp(r.score) for r in result) == sum(exp(r.score) for r in rows)
    before = {r.token: r for r in rows}
    for row in result:
        original = before[row.token]
        assert row.features is original.features
        assert row.plausibility == original.plausibility
        assert row.score_breakdown["intent"] == original.score_breakdown["intent"]
        assert (
            row.score_breakdown["intent"] + row.score_breakdown["selection_constraint"] == row.score
        )
        assert row.score_breakdown["total"] == row.score
    assert all("selection_constraint" not in r.score_breakdown for r in rows)


@pytest.mark.parametrize(
    "intent,preset",
    [
        (None, "balanced"),
        ({}, "balanced"),
        ({"darker_brighter": 0}, "balanced"),
        ({"darker_brighter": 0.1}, "balanced"),
        ({"darker_brighter": 0.7, "smooth": 0.1}, "balanced"),
        ({"darker_brighter": 0.7, "smooth": 0.7}, "balanced"),
        ({"smooth": 0.7}, "balanced"),
        ({"darker_brighter": 0.7}, "plausible"),
        ({"darker_brighter": 0.7}, "adventurous"),
    ],
)
def test_weak_neutral_joint_infeasible_and_other_presets_are_identical(intent, preset):
    rows = ranked()
    assert select_strong_adjacent(rows, intent, preset=preset) is rows


def test_only_top_two_can_change_even_for_twenty_results():
    first, second = ranked()
    rows = [first, second, *(replace(first, token=f"M:{i}") for i in range(18))]
    result = select_strong_adjacent(rows, {"darker_brighter": 0.7})
    assert len(result) == 20
    assert result[2:] == rows[2:]
    assert select_strong_adjacent(rows[::-1], {"darker_brighter": 0.7}) == rows[::-1]
    assert select_strong_adjacent([], {"smooth": 0.7}) == []
    assert select_strong_adjacent(rows[:1], {"smooth": 0.7}) == rows[:1]


def _controlled_scorer(features, *, limit, **kwargs):
    """Utility fixture forces the independently validated selection transition."""
    indexed = {row.token: row for row in features}
    tokens = ["M:V", "M:IV", *(row.token for row in features if row.token not in {"M:V", "M:IV"})]
    result = []
    for i, token in enumerate(tokens[:limit]):
        feature = indexed[token]
        color = dict.fromkeys(feature.color_delta, 0.0)
        color["brightness"] = 0.2 if i == 1 else -0.2
        feature = replace(feature, color_delta=color)
        utility = 3.0 - i / 10
        result.append(
            ScoredCandidate(token, utility, 0.05, {"intent": utility, "total": utility}, feature)
        )
    return result


def test_service_http_and_assistant_preserve_selection_for_all_limit_prefixes(monkeypatch):
    monkeypatch.setattr("app.services.recommend.score_candidates", _controlled_scorer)
    service = _service()
    app.dependency_overrides[recommendation_service] = lambda: service
    try:
        client = TestClient(app)
        requests = {}
        for limit in (1, 2, 5, 20):
            response = client.post(
                "/v2/recommend-next-chords",
                json={
                    "progression": ["C", "G", "Am"],
                    "key": "C major",
                    "intent": {"darker_brighter": 0.7},
                    "limit": limit,
                },
            )
            assert response.status_code == 200
            result = response.json()["data"]["recommendations"]
            assert len(result) == limit
            assert result[0]["token"] == "M:IV"
            assert sum(row["score"] for row in result) == pytest.approx(1.0)
            assert all(a["score"] >= b["score"] for a, b in zip(result, result[1:], strict=False))
            candidates = [
                AssistantCandidate(
                    chords=[row["chord"]],
                    score=row["score"],
                    source_tool="recommend_next",
                    fact_ids=row["fact_ids"],
                )
                for row in result
            ]
            downstream = AssistantWorkflow(None)._rank({"validated_candidates": candidates})
            assert downstream["validated_candidates"] == candidates
            requests[limit] = [row["token"] for row in result]
        assert all(tokens == requests[20][:limit] for limit, tokens in requests.items())
        for preset in ("plausible", "adventurous"):
            response = client.post(
                "/v2/recommend-next-chords",
                json={
                    "progression": ["C", "G", "Am"],
                    "key": "C major",
                    "intent": {"darker_brighter": 0.7},
                    "preset": preset,
                    "limit": 2,
                },
            )
            assert response.status_code == 200
            assert response.json()["data"]["recommendations"][0]["token"] == "M:V"
    finally:
        app.dependency_overrides.pop(recommendation_service, None)


def test_joint_qualifier_and_strong_boundary_and_negative_target():
    first, second = ranked()
    joint = [
        replace(
            first,
            features=replace(
                first.features, color_delta={**first.features.color_delta, "smoothness": -0.2}
            ),
        ),
        replace(
            second,
            features=replace(
                second.features, color_delta={**second.features.color_delta, "smoothness": 0.2}
            ),
        ),
    ]
    assert (
        select_strong_adjacent(joint, {"darker_brighter": 0.7, "smooth": 0.7})[0].token
        == second.token
    )
    assert select_strong_adjacent(joint, {"darker_brighter": 0.699999, "smooth": 0.7}) is joint
    negative = [
        replace(first, features=second.features),
        replace(
            second,
            features=replace(
                first.features, color_delta={**first.features.color_delta, "brightness": -0.2}
            ),
        ),
    ]
    assert select_strong_adjacent(negative, {"darker_brighter": -0.7})[0].token == second.token
    assert select_strong_adjacent(negative, {"darker_brighter": -0.699999}) is negative


@pytest.mark.parametrize("intent", [{"darker_brighter": 0.7}, {"common_surprising": 0.7}])
def test_service_bypasses_selection_and_extra_scoring_for_vector_sources(monkeypatch, intent):
    from app.schemas.recommend_v2 import RecommendRequest

    class Reader:
        def read(self, history, tokens):
            return [], [("M:IV", 0.8)]

        def similarities(self, previous, tokens):
            return {}

    observed_limits = []

    def scorer(features, *, limit, **kwargs):
        observed_limits.append(limit)
        return _controlled_scorer(features, limit=limit, **kwargs)

    monkeypatch.setattr("app.services.recommend.score_candidates", scorer)
    service = _service()
    service.candidate_reader = Reader()
    for limit in (1, 2, 5, 20):
        result = service.recommend(
            RecommendRequest(
                progression=["C", "G", "Am"],
                key="C major",
                intent=intent,
                limit=limit,
            )
        ).data.recommendations
        assert result[0].token == "M:V"
        assert len(result) == limit
    assert observed_limits == [1, 2, 5, 20]


@pytest.mark.parametrize("similarity", [0.0, 0.8])
@pytest.mark.parametrize("intent", [{"darker_brighter": 0.7}, {"common_surprising": 0.7}])
def test_service_bypasses_retained_vector_features_even_without_embedding_neighbors(
    monkeypatch, similarity, intent
):
    from app.schemas.recommend_v2 import RecommendRequest

    class Reader:
        def read(self, history, tokens):
            return [], []

        def similarities(self, previous, tokens):
            return {"M:IV": similarity}

    observed_limits = []

    def scorer(features, *, limit, **kwargs):
        observed_limits.append(limit)
        assert any(row.values["emb_cos"] == similarity for row in features)
        return _controlled_scorer(features, limit=limit, **kwargs)

    monkeypatch.setattr("app.services.recommend.score_candidates", scorer)
    service = _service()
    service.candidate_reader = Reader()
    for limit in (1, 2, 5, 20):
        result = service.recommend(
            RecommendRequest(
                progression=["C", "G", "Am"],
                key="C major",
                intent=intent,
                limit=limit,
            )
        ).data.recommendations
        assert result[0].token == "M:V"
        assert len(result) == limit
    assert observed_limits == [1, 2, 5, 20]


def _surprise_rows(values):
    first = ranked()[0]
    return [
        replace(
            first,
            token=token,
            score=3.0 - i,
            plausibility=0.4 - i * 0.05,
            score_breakdown={"intent": 3.0 - i, "total": 3.0 - i},
            features=replace(
                first.features, color_delta={**first.features.color_delta, "surprise": value}
            ),
        )
        for i, (token, value) in enumerate(
            zip(("M:I", "M:V", "M:IV", "M:ii", "M:vi"), values, strict=False)
        )
    ]


def test_three_slot_rotation_preserves_utility_evidence_and_all_other_components():
    rows = _surprise_rows([0.4, 0.5, 0.8, 0.9, 0.9])
    result = select_bounded_intent(rows, {"common_surprising": 0.7})
    assert [r.token for r in result] == [rows[i].token for i in (2, 0, 1, 3, 4)]
    assert [r.score for r in result] == [r.score for r in rows]
    before = {r.token: r for r in rows}
    for row in result:
        old = before[row.token]
        assert row.plausibility == old.plausibility and row.features is old.features
        assert row.score_breakdown["total"] == row.score
        assert row.score_breakdown["intent"] == old.score_breakdown["intent"]
        assert (
            row.score_breakdown["intent"] + row.score_breakdown.get("selection_constraint", 0)
            == row.score
        )
    assert result[3:] == rows[3:]


@pytest.mark.parametrize(
    "intent,preset",
    [
        ({"common_surprising": 0.69999}, "balanced"),
        ({"common_surprising": -0.7}, "balanced"),
        ({"common_surprising": 0.7, "smooth": 0.7}, "balanced"),
        ({"common_surprising": 0.7, "smooth": 0.1}, "balanced"),
        ({"common_surprising": 0.7}, "plausible"),
        ({"common_surprising": 0.7}, "adventurous"),
        ({"darker_brighter": 0.7}, "balanced"),
        (None, "balanced"),
        ({}, "balanced"),
    ],
)
def test_extended_selector_keeps_all_other_adjacent_branches_exact(intent, preset):
    rows = _surprise_rows([0.4, 0.5, 0.8, 0.9, 0.9])
    assert select_bounded_intent(rows, intent, preset=preset) == select_strong_adjacent(
        rows, intent, preset=preset
    )


@pytest.mark.parametrize("values", [[0.8, 0.4, 0.9], [0.4, 0.8, 0.9], [0.4, 0.5, 0.51], [0.4, 0.5]])
def test_extended_selector_preserves_adjacent_for_existing_or_absent_qualifiers(values):
    rows = _surprise_rows(values)
    assert select_bounded_intent(rows, {"common_surprising": 0.7}) == select_strong_adjacent(
        rows, {"common_surprising": 0.7}
    )


def test_surprise_http_service_assistant_three_slot_prefix_and_source_evidence(monkeypatch):
    observed_limits = []

    def scorer(features, *, limit, **kwargs):
        observed_limits.append(limit)
        rows = _controlled_scorer(features, limit=limit, **kwargs)
        return [
            replace(
                row,
                features=replace(
                    row.features,
                    color_delta={
                        **row.features.color_delta,
                        "surprise": (0.4, 0.5, 0.8)[i] if i < 3 else 0.9,
                    },
                ),
            )
            for i, row in enumerate(rows)
        ]

    monkeypatch.setattr("app.services.recommend.score_candidates", scorer)
    service = _service()
    app.dependency_overrides[recommendation_service] = lambda: service
    try:
        client = TestClient(app)
        outputs = {}
        for limit in (1, 2, 5, 20):
            response = client.post(
                "/v2/recommend-next-chords",
                json={
                    "progression": ["C", "G", "Am"],
                    "key": "C major",
                    "intent": {"common_surprising": 0.7},
                    "limit": limit,
                },
            )
            assert response.status_code == 200
            rows = response.json()["data"]["recommendations"]
            assert len(rows) == limit
            # Third incumbent follows V/IV in the controlled utility fixture.
            assert rows[0]["token"] not in {"M:V", "M:IV"}
            assert sum(r["score"] for r in rows) == pytest.approx(1.0)
            assert all(a["score"] >= b["score"] for a, b in zip(rows, rows[1:], strict=False))
            candidates = [
                AssistantCandidate(
                    chords=[r["chord"]],
                    score=r["score"],
                    source_tool="recommend_next",
                    fact_ids=r["fact_ids"],
                )
                for r in rows
            ]
            assert (
                AssistantWorkflow(None)._rank({"validated_candidates": candidates})[
                    "validated_candidates"
                ]
                == candidates
            )
            outputs[limit] = rows
        assert observed_limits == [3, 3, 5, 20]
        for limit, rows in outputs.items():
            assert [r["token"] for r in rows] == [r["token"] for r in outputs[20][:limit]]
            for a, b in zip(rows, outputs[20], strict=False):
                assert a["evidence"] == b["evidence"]
                assert a["score_breakdown"] == b["score_breakdown"]
                assert a["generators"] == b["generators"]
                assert a["fact_ids"] == b["fact_ids"]
    finally:
        app.dependency_overrides.pop(recommendation_service, None)
