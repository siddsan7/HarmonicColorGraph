"""`color` stage: measurable color features and perceptual-axis norms.
Scheduled for F41 (feature-specs/v2-implementation-plan.md, M4)."""

from __future__ import annotations

from pathlib import Path

from pipeline.stages._unimplemented import StageNotImplementedError


def run_color(sections_path: str | Path, output_path: str | Path) -> None:
    raise StageNotImplementedError("color", "F41")
