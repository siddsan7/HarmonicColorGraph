"""Ground assistant claims in tool output and the relationship registry."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from app.ai.state import Claim, ExplanationDraft
from app.ai.text import chord_mentions, figure_mentions
from app.theory.language import lint_objective_emotion
from app.theory.relationships_v2 import RULES

_REGISTRY = {rule.id for rule in RULES}
_CADENCES = {rule.name.lower() for rule in RULES if rule.name.endswith("cadence")}
_SONG = re.compile(
    r"\b(?:song|track|artist|album|recording|spotify|beatles)\b|"
    r"\b(?:performed|recorded|released)\s+by\b|\b(?:in|from)\s+[\"“][^\"”]+[\"”]",
    re.IGNORECASE,
)
_TITLE = re.compile(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,}\b")
_CADENCE = re.compile(r"\b([a-z][a-z-]*)\s+cadence\b", re.IGNORECASE)
_RELATIONSHIP = re.compile(r"\brelationship:([a-z][a-z0-9_]*)\b", re.IGNORECASE)


def _symbols(tool_results: Mapping[str, Any]) -> tuple[set[str], set[str]]:
    chords: set[str] = set()
    figures: set[str] = set()

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                if key in {"symbol", "raw_symbol", "chord"} and isinstance(item, str):
                    chords.add(item)
                elif key == "chords" and isinstance(item, list):
                    chords.update(symbol for symbol in item if isinstance(symbol, str))
                elif key in {"figure", "display_figure"} and isinstance(item, str):
                    figures.add(item)
                elif key == "core" and isinstance(item, str) and ":" in item:
                    figures.add(item.split(":", 1)[1])
                visit(item)
        elif isinstance(value, list):
            for item in value:
                visit(item)

    visit(dict(tool_results))
    return chords, figures


def validate_claims(
    claims: list[Claim],
    fact_pool: Mapping[str, Any],
    tool_results: Mapping[str, Any],
) -> list[str]:
    """Return stable rule codes for any unsupported claim, without leaking prose."""
    allowed_chords, allowed_figures = _symbols(tool_results)
    violations: list[str] = []
    for index, claim in enumerate(claims):
        prefix = f"claim:{index}:"
        cited = set(claim.fact_ids)
        if not cited or not cited <= set(fact_pool):
            violations.append(prefix + "fact_coverage")
        if chord_mentions(claim.text) - allowed_chords:
            violations.append(prefix + "chord_provenance")
        if figure_mentions(claim.text) - allowed_figures:
            violations.append(prefix + "figure_provenance")
        if lint_objective_emotion(claim.text):
            violations.append(prefix + "objective_emotion")
        if (_SONG.search(claim.text) or _TITLE.search(claim.text)) and not any(
            fact_id.startswith("example:") and fact_id in fact_pool for fact_id in cited
        ):
            violations.append(prefix + "song_provenance")
        if any(label not in _REGISTRY for label in claim.theory_labels):
            violations.append(prefix + "theory_registry")
        if any(match.group(1) not in _REGISTRY for match in _RELATIONSHIP.finditer(claim.text)):
            violations.append(prefix + "theory_registry")
        if any(
            match.group(0).lower() not in _CADENCES
            and match.group(1).lower() not in {"a", "an", "the", "this", "that", "each"}
            for match in _CADENCE.finditer(claim.text)
        ):
            violations.append(prefix + "theory_registry")
        if any(
            fact_id.startswith("relationship:") and fact_id.split(":", 2)[1] not in _REGISTRY
            for fact_id in cited
        ):
            violations.append(prefix + "theory_registry")
    return list(dict.fromkeys(violations))


def validate_draft(
    draft: ExplanationDraft,
    fact_pool: Mapping[str, Any],
    tool_results: Mapping[str, Any],
) -> None:
    """Reject a draft before any model-written text reaches the response."""
    violations = validate_claims(draft.claims, fact_pool, tool_results)
    if violations:
        raise ValueError(",".join(violations))
