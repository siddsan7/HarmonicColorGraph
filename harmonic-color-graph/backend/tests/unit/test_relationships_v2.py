"""Two positive contexts and a counterexample for every catalog rule."""

import pytest

from app.theory.relationships_v2 import RULES
from app.theory.roman import analyze_v2

CASES = {
    "authentic": (("G C", "C major"), ("E7 Am", "A minor"), ("C D", "C major")),
    "half": (("F G", "C major"), ("Dm G", "C major"), ("C D", "C major")),
    "plagal": (("F C", "C major"), ("G D", "D major"), ("C D", "C major")),
    "minor_plagal": (("Fm C", "C major"), ("Gm D", "D major"), ("F C", "C major")),
    "deceptive": (("G Am", "C major"), ("E7 F", "A minor"), ("G C", "C major")),
    "secondary_dominant": (("D7 G", "C major"), ("E7 Am", "C major"), ("C D", "C major")),
    "applied_lt": (("F#dim G", "C major"), ("G#dim A", "D major"), ("C D", "C major")),
    "tritone_sub": (("Db7 C", "C major"), ("Ab7 G", "C major"), ("C D", "C major")),
    "backdoor": (("Bb7 C", "C major"), ("Eb7 F", "F major"), ("C D", "C major")),
    "backdoor_three": (("Fm7 Bb7 C", "C major"), ("Bbm7 Eb7 F", "F major"), ("C D", "C major")),
    "aeolian": (("Ab Bb C", "C major"), ("Bb C D", "D major"), ("C D", "C major")),
    "double_plagal": (("Bb F C", "C major"), ("C G D", "D major"), ("C D", "C major")),
    "circle_fifths": (("Dm G", "C major"), ("Am Dm", "C major"), ("C D", "C major")),
    "chromatic_mediant": (("C Eb", "C major"), ("C Ab", "C major"), ("C D", "C major")),
    "relative": (("C Am", "C major"), ("Am C", "C major"), ("C D", "C major")),
    "parallel": (("C Cm", "C major"), ("Cm C", "C major"), ("C D", "C major")),
    "picardy": (("E7 A", "A minor"), ("F#7 B", "B minor"), ("E7 Am", "A minor")),
    "stepwise_bass": (("C Dm", "C major"), ("C/E F", "C major"), ("C G", "C major")),
    "common_tone": (("C Am", "C major"), ("F Am", "C major"), ("C D", "C major")),
    "neapolitan_to_v": (("Db G", "C major"), ("Eb A", "D major"), ("C D", "C major")),
}


def _labels(chords: str, key: str) -> set[str]:
    return {fact.id for fact in analyze_v2(chords, key).relationships}


@pytest.mark.parametrize("rule_id", CASES)
def test_rule_has_two_positive_examples_and_one_negative(rule_id):
    first, second, negative = CASES[rule_id]
    assert rule_id in _labels(*first)
    assert rule_id in _labels(*second)
    assert rule_id not in _labels(*negative)


def test_cases_cover_full_registry():
    assert set(CASES) == {rule.id for rule in RULES}
    assert len(RULES) >= 20
    assert all(rule.arity in {2, 3} for rule in RULES)


def test_relationship_facts_have_stable_ids():
    result = analyze_v2("D7 G C", "C major")
    assert all(
        fact.fact_ids == [f"relationship:{fact.id}:{fact.from_index}:{fact.to_index}"]
        for fact in result.relationships
    )
