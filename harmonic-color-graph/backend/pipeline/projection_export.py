"""Publish the offline embedding projection as a small browser snapshot."""

import json
from pathlib import Path

MAP_MODEL = "chord2vec"  # Pattern vectors are only trained for this model.


def export_projection(source: Path, destination: Path) -> int:
    import polars as pl

    projected = pl.read_parquet(source).filter(pl.col("model") == MAP_MODEL)
    functions = projected.filter(pl.col("subject_type") == "function")
    selected_functions = functions.head(500)
    patterns = projected.filter(pl.col("subject_type") == "pattern").head(
        5000 - len(selected_functions)
    )
    remaining = 5000 - len(selected_functions) - len(patterns)
    frame = pl.concat([selected_functions, patterns, functions.slice(500, remaining)])
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
        json.dumps({"model": MAP_MODEL, "points": points}, separators=(",", ":")), encoding="utf-8"
    )
    return len(points)
