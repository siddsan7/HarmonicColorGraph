"""Static integrity of the live-model F72 adversarial corpus."""

from tests.eval.ai_adversarial import load_cases


def test_adversarial_corpus_has_all_required_categories():
    cases = load_cases()
    assert len(cases) >= 25
    assert {case["id"].split("-", 1)[0] for case in cases} == {
        "song",
        "emotion",
        "invent",
        "nonsense",
        "inject",
    }
    assert all(case["prompt"] and case["must_not"] for case in cases)
