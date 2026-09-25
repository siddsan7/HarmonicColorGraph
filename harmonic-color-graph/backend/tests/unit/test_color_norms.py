"""F41 color/norms.py: percentile-based [0, 1] normalization."""

from app.color.norms import AxisNorm, index_norms, normalize


def _norm(**overrides) -> AxisNorm:
    defaults = dict(
        axis="tension",
        subject_type="transition",
        count=1000,
        p05=0.1,
        p25=0.3,
        p50=0.5,
        p75=0.7,
        p95=0.9,
        mean=0.5,
        std=0.2,
    )
    defaults.update(overrides)
    return AxisNorm(**defaults)


def test_normalize_maps_median_near_midpoint():
    norm = _norm()
    assert abs(normalize(0.5, norm) - 0.5) < 1e-9


def test_normalize_clips_below_p05_to_zero():
    norm = _norm()
    assert normalize(-1.0, norm) == 0.0


def test_normalize_clips_above_p95_to_one():
    norm = _norm()
    assert normalize(5.0, norm) == 1.0


def test_normalize_handles_degenerate_zero_span():
    norm = _norm(p05=0.5, p95=0.5)
    assert normalize(0.5, norm) == 0.5


def test_axis_norm_from_row_coerces_types():
    row = {
        "axis": "brightness",
        "subject_type": "chord",
        "count": "42",
        "p05": "0.1",
        "p25": "0.2",
        "p50": "0.3",
        "p75": "0.4",
        "p95": "0.5",
        "mean": "0.3",
        "std": "0.1",
    }
    norm = AxisNorm.from_row(row)
    assert norm.count == 42
    assert norm.p50 == 0.3


def test_index_norms_keys_by_axis_and_subject_type():
    rows = [
        {
            "axis": "tension",
            "subject_type": "chord",
            "count": 10,
            "p05": 0.0,
            "p25": 0.1,
            "p50": 0.2,
            "p75": 0.3,
            "p95": 0.4,
            "mean": 0.2,
            "std": 0.1,
        },
        {
            "axis": "tension",
            "subject_type": "transition",
            "count": 20,
            "p05": 0.1,
            "p25": 0.2,
            "p50": 0.3,
            "p75": 0.4,
            "p95": 0.5,
            "mean": 0.3,
            "std": 0.1,
        },
    ]
    table = index_norms(rows)
    assert set(table) == {("tension", "chord"), ("tension", "transition")}
    assert table[("tension", "chord")].count == 10
