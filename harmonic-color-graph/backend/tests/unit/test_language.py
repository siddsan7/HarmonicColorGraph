"""Creator-facing catalog text must avoid objective emotion claims."""

import re

from app.theory.relationships_v2 import RULES

OBJECTIVE_EMOTION = re.compile(
    r"\b(is|means|makes you)\s+(sad|happy|nostalgic|dreamy|hopeful|tense)\b",
    re.IGNORECASE,
)


def test_all_relationship_templates_hedge_emotional_language():
    for rule in RULES:
        assert not OBJECTIVE_EMOTION.search(rule.fact_template), rule.id
        assert not OBJECTIVE_EMOTION.search(rule.technical_template), rule.id
