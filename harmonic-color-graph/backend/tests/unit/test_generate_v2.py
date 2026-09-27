"""F60 constraints, ranking quality, diversity, latency, and HTTP contract."""

import random
from statistics import mean

from fastapi.testclient import TestClient

from app.api.recommend_v2 import recommendation_service
from app.main import app
from app.predict.ngram import InMemoryNgramStore, KNPredictor
from app.recommend.generate import ProgressionGenerator, _edit_distance
from app.schemas.generate_v2 import GenerateRequest, GenerateResponse
from app.services.recommend import RecommendationService
from tests.unit.test_recommend_v2_api import Examples, Facts, _service


def _seeded_service(seed: int) -> RecommendationService:
    rng = random.Random(seed)
    counts = {
        token: rng.randint(10, 90) for token in ("M:I", "M:ii", "M:IV", "M:V", "M:V7", "M:vi")
    }
    store = InMemoryNgramStore(version=f"f60-{seed}")
    store.add_row(
        "global",
        1,
        "",
        total=sum(counts.values()),
        distinct_next=len(counts),
        next=counts,
        cont=counts,
    )
    return RecommendationService(KNPredictor(store), Examples(), Facts())


def _rank(values: list[float]) -> list[float]:
    return [
        mean(i + 1 for i, other in enumerate(sorted(values)) if other == value) for value in values
    ]


def _spearman(left: list[float], right: list[float]) -> float:
    a, b = _rank(left), _rank(right)
    a_mean, b_mean = mean(a), mean(b)
    numerator = sum((x - a_mean) * (y - b_mean) for x, y in zip(a, b, strict=True))
    denominator = (sum((x - a_mean) ** 2 for x in a) * sum((y - b_mean) ** 2 for y in b)) ** 0.5
    return numerator / denominator if denominator else 0.0


def test_constraints_and_realized_response():
    result = ProgressionGenerator(_service()).generate(
        GenerateRequest(
            key="C major",
            length=4,
            k=2,
            start="C",
            end="M:I",
            required_chords={1: "M:IV"},
            cadence="authentic",
            max_chromaticity=0,
        )
    )
    assert result.paths
    assert GenerateResponse.model_validate(result.model_dump()) == result
    for path in result.paths:
        assert len(path.tokens) == len(path.steps) == 4
        assert path.tokens[0] == path.tokens[-1] == "M:I"
        assert path.tokens[1] == "M:IV"
        assert path.tokens[-2] in {"M:V", "M:V7", "M:vii", "M:viio7"}
        assert any(fact.id == "authentic" for fact in path.facts)
        assert all((step.color["chromaticity"] or 0) <= 0 for step in path.steps)
        assert all(len(step.voicing) == 4 for step in path.steps)
        assert all(
            step.explanation and step.score_breakdown and step.sources for step in path.steps
        )
    if len(result.paths) == 2:
        assert _edit_distance(tuple(result.paths[0].tokens), tuple(result.paths[1].tokens)) >= 2


def test_infeasible_constraints_return_no_paths():
    result = ProgressionGenerator(_service()).generate(
        GenerateRequest(
            key="C major",
            length=2,
            end="M:I",
            cadence="half",
            k=2,
        )
    )
    assert result.paths == []
    assert result.warnings


def test_http_contract_and_validation():
    app.dependency_overrides[recommendation_service] = _service
    try:
        client = TestClient(app)
        response = client.post(
            "/v2/generate-progression",
            json={
                "key": "C major",
                "length": 3,
                "k": 1,
                "start": "M:I",
                "required_chords": {"1": "M:V"},
                "end": "M:I",
                "cadence": "authentic",
            },
        )
        assert response.status_code == 200
        assert GenerateResponse.model_validate(response.json()).paths[0].tokens == [
            "M:I",
            "M:V",
            "M:I",
        ]
        invalid = client.post(
            "/v2/generate-progression",
            json={
                "key": "C major",
                "length": 3,
                "required_chords": {"3": "M:I"},
            },
        )
        assert invalid.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_hard_constraints_over_200_valid_requests():
    rng = random.Random(60)
    generator = ProgressionGenerator(_seeded_service(60))
    keys = ("C major", "G major", "A minor", "E minor")
    for _ in range(200):
        key = rng.choice(keys)
        choices = (
            ["M:I", "M:ii", "M:IV", "M:V", "M:vi"]
            if key.endswith("major")
            else ["m:i", "m:III", "m:iv", "m:VI"]
        )
        length = rng.randint(2, 5)
        start, end = rng.choice(choices), rng.choice(choices)
        position = rng.randrange(1, length - 1) if length > 2 else None
        required = {position: rng.choice(choices)} if position is not None else {}
        request = GenerateRequest(
            key=key,
            length=length,
            k=rng.randint(1, 3),
            start=start,
            end=end,
            required_chords=required,
            max_chromaticity=0.0,
            tension_curve=rng.choice(["rise_then_resolve", "arch", "plateau"]),
        )
        result = generator.generate(request)
        assert result.paths
        for path in result.paths:
            assert len(path.tokens) == length
            assert all(
                token.startswith("M:" if key.endswith("major") else "m:") for token in path.tokens
            )
            assert path.tokens[0] == start and path.tokens[-1] == end
            assert all(path.tokens[index] == token for index, token in required.items())
            assert all(step.color["chromaticity"] <= 0 for step in path.steps)
        for i, left in enumerate(result.paths):
            for right in result.paths[i + 1 :]:
                assert _edit_distance(tuple(left.tokens), tuple(right.tokens)) >= 2


def test_rise_then_resolve_curve_on_30_corpus_seeds():
    target = [0.0, 1 / 3, 2 / 3, 1.0, 0.5, 0.0]
    correlations = []
    latencies = []
    for seed in range(30):
        result = ProgressionGenerator(_seeded_service(seed)).generate(
            GenerateRequest(
                key="C major",
                length=6,
                k=1,
                tension_curve="rise_then_resolve",
            )
        )
        assert result.paths
        arc = [step.color["tension"] for step in result.paths[0].steps]
        correlations.append(_spearman(arc, target))
        latencies.append(result.latency_ms)
    assert sum(value >= 0.7 for value in correlations) >= 24, correlations
    assert sorted(latencies)[28] < 2000, sorted(latencies)


def test_five_distinct_paths_when_unconstrained():
    for seed in range(5):
        result = ProgressionGenerator(_seeded_service(seed)).generate(
            GenerateRequest(
                key="C major",
                length=6,
                k=5,
            )
        )
        assert len(result.paths) == 5
        assert all(
            _edit_distance(tuple(left.tokens), tuple(right.tokens)) >= 2
            for index, left in enumerate(result.paths)
            for right in result.paths[index + 1 :]
        )


def test_cadences_and_borrowed_demo_path():
    generator = ProgressionGenerator(_seeded_service(4))
    cases = [
        ("C major", "M:V", "M:I", "authentic"),
        ("C major", "M:IV", "M:I", "plagal"),
        ("A minor", "m:iv", "m:i", "plagal"),
        ("C major", "M:V", "M:vi", "deceptive"),
        ("C major", "M:IV", "M:V", "half"),
    ]
    for key, start, end, cadence in cases:
        result = generator.generate(
            GenerateRequest(
                key=key,
                length=2,
                k=1,
                start=start,
                end=end,
                cadence=cadence,
            )
        )
        assert result.paths, (key, cadence)
        assert result.paths[0].tokens == [start, end]
        assert any(fact.category == "cadence" for fact in result.paths[0].facts)
    demo = generator.generate(
        GenerateRequest(
            key="C major",
            length=4,
            k=1,
            start="C",
            end="C",
            required_chords={1: "F", 2: "Fm"},
        )
    )
    assert demo.paths[0].chords == ["C", "F", "Fm", "C"]


def test_allowed_genre_uses_retained_context_or_reports_none():
    service = _service()
    generator = ProgressionGenerator(service)
    pop = generator.generate(
        GenerateRequest(
            key="C major",
            length=2,
            k=1,
            allowed_genres=["missing", "pop"],
        )
    )
    assert pop.genre == "pop" and pop.paths
    missing = generator.generate(
        GenerateRequest(
            key="C major",
            length=2,
            k=1,
            allowed_genres=["missing"],
        )
    )
    assert missing.paths == [] and missing.warnings


def test_required_extended_chord_is_preserved():
    result = ProgressionGenerator(_seeded_service(8)).generate(
        GenerateRequest(
            key="C major",
            length=2,
            k=1,
            start="Cmaj9",
            end="G7",
        )
    )
    assert result.paths[0].chords == ["Cmaj9", "G7"]
    assert result.paths[0].steps[0].pitch_classes != [0, 4, 7, 11]


def test_max_chromaticity_checks_entire_chord_not_only_new_tones():
    result = ProgressionGenerator(_seeded_service(8)).generate(
        GenerateRequest(
            key="C major",
            length=2,
            k=1,
            start="Bb",
            end="Bb7",
            max_chromaticity=0.34,
        )
    )
    assert result.paths == []
