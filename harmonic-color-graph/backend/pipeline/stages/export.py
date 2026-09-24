"""`export` stage: interop exports from the build artifacts (e.g. the
Neo4j/Cypher export in feature-specs/v2-implementation-plan.md's Stretch
§S1). Not scheduled against a numbered feature yet."""

from __future__ import annotations

from pathlib import Path

from pipeline.stages._unimplemented import StageNotImplementedError


def run_export(sections_path: str | Path, output_path: str | Path) -> None:
    raise StageNotImplementedError("export", "a future feature (see plan Stretch §S1)")
