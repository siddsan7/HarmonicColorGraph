"""Shared lint for claims that present a subjective emotion as objective fact."""

import re

_EMOTION = (
    r"sad|sadness|happy|happiness|nostalgic|nostalgia|dreamy|dreaminess|"
    r"hopeful|hopefulness|tense|dark|uplifting|melancholic|melancholy"
)
OBJECTIVE_EMOTION = re.compile(rf"\b(?:{_EMOTION})\b", re.IGNORECASE)
_HEDGE = re.compile(
    r"\b(?:may|might|can|could|often|sometimes|commonly|tends? to|"
    r"some listeners?|many listeners?)\b",
    re.IGNORECASE,
)


def lint_objective_emotion(text: str) -> bool:
    """Flag unhedged emotion assertions; return False for factual or hedged text."""
    for match in OBJECTIVE_EMOTION.finditer(text):
        sentence_start = max(text.rfind(mark, 0, match.start()) for mark in ".!?") + 1
        if not _HEDGE.search(text[sentence_start : match.start()]):
            return True
    return False
