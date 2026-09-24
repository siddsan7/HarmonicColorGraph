"""`snapshot` stage: static `public/snapshot/graph-core.json` degraded-mode
fallback (global function graph, top edges, <= 500 KB).
Scheduled for F63 (feature-specs/v2-implementation-plan.md, M6)."""

from __future__ import annotations

from pathlib import Path

from pipeline.stages._unimplemented import StageNotImplementedError


def run_snapshot(sections_path: str | Path, output_path: str | Path) -> None:
    raise StageNotImplementedError("snapshot", "F63")
