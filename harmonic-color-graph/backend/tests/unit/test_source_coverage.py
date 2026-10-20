"""Graph parity must preserve runtime source selection and source attribution."""

from app.predict.ngram import InMemoryNgramStore, KNPredictor
from tests.eval.sampling import SampledPosition
from tests.eval.source_coverage import PROTOCOL, graph_neighbors, measure


def edge(token, prob=0.01, source="M:I", context="global"):
    return {"from_token": source, "to_token": token, "prob": prob, "context": context}


def test_graph_selection_matches_production_threshold_context_mode_and_order():
    rows = [
        edge("M:V", 0.2),
        edge("M:IV", 0.2),
        edge("M:ii", 0.005),
        edge("M:vi", 0.0049),
        edge("m:i", 0.3),
        edge("M:iii", 0.4, context="section:verse"),
        edge("M:bVII", 0.4, source="M:V"),
    ]
    assert graph_neighbors(rows, "M:I") == [("M:IV", 0.2), ("M:V", 0.2), ("M:ii", 0.005)]


def test_graph_bound_remains_thirty_and_ties_are_stable():
    rows = [edge(f"M:token-{index:03}") for index in range(100)]
    assert len(graph_neighbors(rows, "M:I")) == 30
    assert graph_neighbors(rows, "M:I") == graph_neighbors(list(reversed(rows)), "M:I")


def test_empty_graph_arms_match_and_categories_partition_original_denominator():
    store = InMemoryNgramStore.from_rows(
        [
            dict(
                context="global",
                order=1,
                history="",
                total=2,
                distinct_next=2,
                next={"M:I": 1, "M:V": 1},
            ),
            dict(
                context="global", order=2, history="M:I", total=1, distinct_next=1, next={"M:V": 1}
            ),
        ]
    )
    position = SampledPosition("sealed", 0, 1, None, None, "major", ("M:I",), "M:V")
    result = measure([position], KNPredictor(store), [])
    assert result["counts"]["ngram_theory"] == result["counts"]["plus_graph"]
    assert sum(result["counts"]["plus_graph"].values()) == len(PROTOCOL["requests"])
    assert result["source"]["neutral_top5_changed"] == 0
    assert result["source"]["novel_graph_candidates"] == 0
    assert result["quality"]["ngram_theory"] == result["quality"]["plus_graph"]
