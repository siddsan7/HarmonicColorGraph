"""The map snapshot preserves projected identities and bounds its size."""

import json

import polars as pl

from pipeline.projection_export import export_projection


def test_export_projection_selects_model_and_caps_points(tmp_path):
    source = tmp_path / "embedding_projection.parquet"
    destination = tmp_path / "embedding-map.json"
    pl.DataFrame(
        {
            "subject_type": ["function"] * 5001 + ["pattern"],
            "subject_id": [f"M:{index}" for index in range(5001)] + ["M:I M:V M:vi"],
            "model": ["chord2vec"] * 5001 + ["fastrp"],
            "x": [float(index) for index in range(5002)],
            "y": [1.0] * 5002,
        }
    ).write_parquet(source)
    assert export_projection(source, destination, "chord2vec") == 5000
    data = json.loads(destination.read_text(encoding="utf-8"))
    assert data["model"] == "chord2vec"
    assert len(data["points"]) == 5000
    assert data["points"][0] == {"type": "function", "id": "M:0", "x": 0.0, "y": 1.0}
