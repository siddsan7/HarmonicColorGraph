"""`aggregate` stage: transitions per context, FUNCTIONS_AS, ABS_TRANSITIONS_TO.
Scheduled for F22 (feature-specs/v2-implementation-plan.md)."""

from __future__ import annotations

from pathlib import Path

from pipeline.stages._unimplemented import StageNotImplementedError


def run_aggregate(sections_path: str | Path, output_path: str | Path) -> None:
    raise StageNotImplementedError("aggregate", "F22")
