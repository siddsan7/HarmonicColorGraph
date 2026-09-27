"""Creator-facing catalog text must avoid objective emotion claims."""

from app.theory.language import lint_objective_emotion
from app.theory.relationships_v2 import RULES


def test_all_relationship_templates_hedge_emotional_language():
    for rule in RULES:
        assert not lint_objective_emotion(rule.fact_template), rule.id
        assert not lint_objective_emotion(rule.technical_template), rule.id
