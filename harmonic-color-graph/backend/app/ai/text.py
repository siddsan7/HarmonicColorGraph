"""Recognize supported chord and Roman-figure mentions in assistant prose."""

from __future__ import annotations

import re

from app.theory.chord_normalizer import QUALITY_ALIASES, normalize_chord

_QUALITY = "|".join(
    re.escape(alias) for alias in sorted(QUALITY_ALIASES, key=len, reverse=True) if alias
)
CHORD_PATTERN = re.compile(
    rf"(?<![\w])(?:[A-G](?:#|b|s)?)(?:{_QUALITY})?"
    r"(?:/[A-G](?:#|b|s)?)?(?![\w/#])"
)
_FIGURE = re.compile(
    r"(?<![\w])(?:[b#]?(?:VII|VI|IV|III|II|V|I|vii|vi|iv|iii|ii|v|i)"
    r"(?:maj13|maj11|maj9|maj7|add13|add11|add9|sus4|sus2|h7|o7|o|ø|\+)?"
    r"(?:13|11|9|7|65|64|43|42|6)?(?:[#b]\d+)?"
    r"(?:/(?:VII|VI|IV|III|II|V|I|vii|vi|iv|iii|ii|v|i))?)(?![\w])"
)


def extract_chords(text: str) -> list[str]:
    """Return exact supported chord spellings without matching word prefixes."""
    return [
        match.group(0)
        for match in CHORD_PATTERN.finditer(text)
        if normalize_chord(match.group(0)).success
    ]


def chord_mentions(text: str) -> set[str]:
    """Detect note symbols in prose while tolerating the article 'A'."""
    matches = list(CHORD_PATTERN.finditer(text))
    mentions: set[str] = set()
    for index, match in enumerate(matches):
        symbol = match.group(0)
        if symbol == "A":
            following = text[match.end() :]
            musical_noun = re.match(r"\s+(?:chord|major|minor|triad|note)\b", following, re.I)
            neighboring_chord = any(
                other.start() - match.end() <= 3 and other.start() > match.start()
                for other in matches[index + 1 : index + 2]
            )
            if not musical_noun and not neighboring_chord:
                continue
        mentions.add(symbol)
    return mentions


def figure_mentions(text: str) -> set[str]:
    """Detect explicit Roman figures; distinguish tonic I from the pronoun."""
    mentions: set[str] = set()
    for match in _FIGURE.finditer(text):
        symbol = match.group(0)
        if symbol == "I" and re.match(
            r"\s+(?:think|feel|would|can|am|have|hear|want|prefer|believe|see|need|like)\b",
            text[match.end() :],
            re.IGNORECASE,
        ):
            continue
        mentions.add(symbol)
    return mentions
