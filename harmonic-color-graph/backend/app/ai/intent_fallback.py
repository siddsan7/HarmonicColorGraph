"""Conservative explicit directions for the model-unavailable parser.

This grammar is a recovery aid, not a substitute for language understanding.
Negated or alternative clauses are omitted, rather than converted into an
opposite preference. Conflicting directions omit that axis. Magnitudes are
product defaults, not measured perceptual strengths.
"""

from __future__ import annotations

import re

_DIRECTIONS = {
    "darker_brighter": ((r"dark(?:er)?", -1), (r"bright(?:er)?", 1)),
    "tense_relaxed": ((r"tense|tenser|tension", -1), (r"relaxed|relaxation", 1)),
    "common_surprising": ((r"common|familiar", -1), (r"surprising|surprise", 1)),
    "simple_complex": ((r"simple|simpler", -1), (r"complex|complexity", 1)),
    "resolved_open": ((r"resolved|resolution", -1), (r"open", 1)),
    "smooth": ((r"smooth|smoother", 1),),
    "dreamy": ((r"dreamy|dreamier|dreamlike", 1),),
}
_CLAUSES = re.compile(r"[.!?;,\n]|\b(?:but|however)\b")
_UNCERTAIN = re.compile(
    r"\b(?:not|no|never|neither|nor|without|avoid|or|unless|whether)\b|\b\w+n['’]t\b"
)
_GENERATE_VERB = r"\b(?:generate|create|make|write|compose)\s+(?:me\s+)?(?:a\s+|the\s+)?"


def explicit_next_chord_command(query: str) -> bool:
    """Recover a direct next-chord object, without resolving mixed requests.

    Generation verbs can request one recommendation. Quoted examples, negation,
    alternatives and explicit requests for a whole progression retain the old
    route. This recovery never changes a valid model-selected route.
    """
    lower = query.lower()
    if _UNCERTAIN.search(lower):
        return False
    unquoted = re.sub(r"'[^'\n]*'|\"[^\"\n]*\"|“[^”\n]*”", "", lower)
    if re.search(_GENERATE_VERB + r"(?:\w+\s+){0,3}(?:progression|sequence|song)\b", unquoted):
        return False
    return bool(re.search(_GENERATE_VERB + r"next\s+chord\b", unquoted))


def explicit_axes(query: str) -> dict[str, float]:
    values: dict[str, list[float]] = {}
    for clause in _CLAUSES.split(query.lower()):
        # Scope abstention to a clause. In particular, 'not dark' does not
        # entail 'bright', and 'dark or bright' is not a combined objective.
        if _UNCERTAIN.search(clause):
            continue
        if re.search(r"\bif\b(?!\s+i\s+(?:want|prefer|request)\b)", clause):
            continue
        for axis, directions in _DIRECTIONS.items():
            for pattern, sign in directions:
                for match in re.finditer(rf"\b(?:{pattern})\b", clause):
                    prefix = clause[: match.start()]
                    direction = -sign if re.search(r"\bless\s+$", prefix) else sign
                    strength = 0.7
                    if re.search(
                        r"\b(?:slightly|a little(?: bit)?|a bit)\s+(?:(?:more|less)\s+)?$", prefix
                    ):
                        strength = 0.3
                    elif re.search(r"\b(?:much|very|far)\s+(?:(?:more|less)\s+)?$", prefix):
                        strength = 1.0
                    values.setdefault(axis, []).append(direction * strength)
    return {
        axis: max(choices, key=abs)
        for axis, choices in values.items()
        if all(value > 0 for value in choices) or all(value < 0 for value in choices)
    }
