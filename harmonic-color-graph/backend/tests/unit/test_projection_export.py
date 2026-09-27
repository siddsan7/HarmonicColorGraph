"""The map snapshot preserves projected identities and bounds its size."""

import json

import polars as pl

from pipeline.projection_export import export_projection


def test_export_projection_selects_model_and_caps_points(tmp_path):
    source = tmp_path / "embedding_projection.parquet"
    destination = tmp_path / "embedding-map.json"
    pl.DataFrame(
        {
            "subject_type": ["function"] * 5001 + ["pattern", "pattern"],
            "subject_id": [f"M:{index}" for index in range(5001)]
            + ["M:I M:V M:vi", "M:vi M:IV M:V"],
            "model": ["chord2vec"] * 5001 + ["fastrp", "chord2vec"],
            "x": [float(index) for index in range(5003)],
            "y": [1.0] * 5003,
        }
    ).write_parquet(source)
    assert export_projection(source, destination) == 5000
    data = json.loads(destination.read_text(encoding="utf-8"))
    assert data["model"] == "chord2vec"
    assert len(data["points"]) == 5000
    assert data["points"][0] == {"type": "function", "id": "M:0", "x": 0.0, "y": 1.0}
    assert any(point["id"] == "M:vi M:IV M:V" for point in data["points"])


def test_map_uses_pattern_model_even_when_fastrp_is_the_default(tmp_path):
    source = tmp_path / "embedding_projection.parquet"
    destination = tmp_path / "embedding-map.json"
    # The evaluated default model can be FastRP, which has no pattern vectors.
    default_model = "fastrp"
    pl.DataFrame(
        {
            "subject_type": ["function", "function", "pattern"],
            "subject_id": ["M:I", "M:V", "M:I M:V M:vi"],
            "model": [default_model, "chord2vec", "chord2vec"],
            "x": [1.0, 2.0, 3.0],
            "y": [4.0, 5.0, 6.0],
        }
    ).write_parquet(source)
    assert export_projection(source, destination) == 2
    data = json.loads(destination.read_text(encoding="utf-8"))
    assert data["model"] == "chord2vec"
    assert {point["id"] for point in data["points"]} == {"M:V", "M:I M:V M:vi"}
