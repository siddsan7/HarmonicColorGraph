"""F41: percentile-based normalization for the raw color axes in
`app/color/features.py`, using corpus breakpoints the `color` pipeline stage
computes into `hcg.color_norms` (one row per axis x subject_type).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AxisNorm:
    """One `hcg.color_norms` row: percentile breakpoints for one axis, for
    either a chord in context (`subject_type="chord"`) or a transition
    (`subject_type="transition"`)."""

    axis: str
    subject_type: str
    count: int
    p05: float
    p25: float
    p50: float
    p75: float
    p95: float
    mean: float
    std: float

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> AxisNorm:
        return cls(
            axis=row["axis"],
            subject_type=row["subject_type"],
            count=int(row["count"]),
            p05=float(row["p05"]),
            p25=float(row["p25"]),
            p50=float(row["p50"]),
            p75=float(row["p75"]),
            p95=float(row["p95"]),
            mean=float(row["mean"]),
            std=float(row["std"]),
        )


def normalize(raw: float, norm: AxisNorm) -> float:
    """Map a raw axis value onto [0, 1] using the corpus's 5th/95th
    percentile as the floor/ceiling. Percentile bounds (not min/max) keep a
    handful of extreme outlier chords from compressing the whole scale; a
    raw value outside [p05, p95] simply clips to 0 or 1.
    """
    span = norm.p95 - norm.p05
    if span <= 0:
        return 0.5
    return max(0.0, min(1.0, (raw - norm.p05) / span))


NormsTable = dict[tuple[str, str], AxisNorm]


def index_norms(rows: list[dict[str, Any]]) -> NormsTable:
    """Build an `(axis, subject_type) -> AxisNorm` lookup from `hcg.color_norms`
    rows (or the `color_norms.parquet` artifact's own rows, same shape)."""
    return {(row["axis"], row["subject_type"]): AxisNorm.from_row(row) for row in rows}
