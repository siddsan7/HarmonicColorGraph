"""Shared marker for pipeline stages this feature has not built yet."""

from __future__ import annotations


class StageNotImplementedError(NotImplementedError):
    """Raised by a stage registered in `pipeline/cli.py`'s `run` command
    whose implementation is scheduled for a later feature.
    """

    def __init__(self, stage: str, feature: str):
        super().__init__(
            f"pipeline stage '{stage}' is not implemented yet "
            f"(scheduled for {feature}; see feature-specs/v2-implementation-plan.md)."
        )
