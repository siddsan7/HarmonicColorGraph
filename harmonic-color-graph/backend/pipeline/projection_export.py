"""Publish the offline embedding projection as a small browser snapshot."""

import json
from pathlib import Path


def export_projection(source: Path, destination: Path, model: str) -> int:
    import polars as pl

    frame = pl.read_parquet(source).filter(pl.col("model") == model).head(5000)
    points = [
        {
            "type": row["subject_type"],
            "id": row["subject_id"],
            "x": round(row["x"], 5),
            "y": round(row["y"], 5),
        }
        for row in frame.iter_rows(named=True)
    ]
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps({"model": model, "points": points}, separators=(",", ":")), encoding="utf-8"
    )
    return len(points)
