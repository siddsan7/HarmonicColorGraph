"""Bounded explanation hints derived from the unchanged validation rules."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from app.ai.validators import _REGISTRY, _symbols

MAX_HINT_BYTES = 2048
# Eight claims can each report six validator codes; retain repair headroom.
REPAIR_HEADROOM_BYTES = 4096
_REPAIR_ADVICE = {
    "fact_coverage": "Cite exact IDs present in facts; do not invent or shorten IDs.",
    "chord_provenance": "Use only chord symbols present in tool_results, or omit chord names.",
    "figure_provenance": "Use only figures present in tool_results, or omit figure names.",
    "objective_emotion": "Describe measured features; do not assert an emotion as objective fact.",
    "song_provenance": "Omit song, artist and title names unless supported by cited example facts.",
    "theory_registry": (
        "Use only registered theory IDs supported by relationship facts, or omit theory labels."
    ),
}


def explanation_hints(facts: Mapping[str, Any], tool_results: Mapping[str, Any]) -> str:
    """Return compact optional hints; full evidence remains authoritative.

    Large evidence must not create another unbounded copy in the prompt. Omit
    hints as a whole when they exceed the cap, rather than imply a partial list
    is the complete set of permitted symbols.
    """
    chords, figures = _symbols(tool_results)
    labels = {
        fact_id.split(":", 2)[1]
        for fact_id in facts
        if fact_id.startswith("relationship:") and len(fact_id.split(":", 2)) >= 2
    } & _REGISTRY
    payload = {
        "chord_symbols": sorted(chords),
        "figure_symbols": sorted(figures),
        "evidenced_theory_ids": sorted(labels),
    }
    hint = (
        "Validation hints from tool evidence (facts and tool_results remain authoritative): "
        + json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        + " Symbol availability alone is not claim support; cite facts that support each claim.\n"
    )
    return hint if len(hint.encode("utf-8")) <= MAX_HINT_BYTES else ""


def repair_advice(codes: tuple[str, ...] = ()) -> str:
    """Map stable validator codes to fixed advice; never quote rejected prose."""
    rules = {code.rsplit(":", 1)[-1] for code in codes}
    advice = [_REPAIR_ADVICE[rule] for rule in _REPAIR_ADVICE if rule in rules]
    return " ".join(advice) or "Return an object with a claims array matching the required schema."
