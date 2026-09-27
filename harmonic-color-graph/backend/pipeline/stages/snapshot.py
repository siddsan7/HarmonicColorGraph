"""Export a bounded global function graph for offline browsing."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

MAX_BYTES = 500_000


def run_snapshot(sections_path: str | Path, output_path: str | Path) -> None:
    import polars as pl

    artifact_dir = Path(output_path).parent
    transitions = pl.read_parquet(artifact_dir / "transitions.parquet")
    transitions = transitions.filter(pl.col("context") == "global").sort(
        ["count", "from_token", "to_token"], descending=[True, False, False]
    )
    colors_path = artifact_dir / "color_profiles.parquet"
    colors = {}
    if colors_path.exists():
        for row in (
            pl.read_parquet(colors_path)
            .filter(pl.col("subject_type") == "function")
            .iter_rows(named=True)
        ):
            colors[row["subject_id"]] = json.loads(row["axes"])
    support: dict[str, int] = defaultdict(int)
    all_edges = []
    for row in transitions.iter_rows(named=True):
        src, dst = row["from_token"], row["to_token"]
        support[src] += int(row["count"])
        support[dst] += int(row["count"])
        all_edges.append(
            {
                "src": f"function:{src}",
                "dst": f"function:{dst}",
                "type": "TRANSITIONS_TO",
                "count": int(row["count"]),
                "prob": float(row["prob"]),
                "props": {"support": int(row["support"]), "pmi": float(row["pmi"])},
            }
        )
    tokens = set(sorted(support, key=lambda token: (-support[token], token))[:120])
    edges = [
        edge
        for edge in all_edges
        if edge["src"].removeprefix("function:") in tokens
        and edge["dst"].removeprefix("function:") in tokens
    ][:1200]
    nodes = []
    for token in sorted(tokens):
        props = {"support": support[token], "chromaticity": 0.0}
        if token in colors:
            props["color"] = colors[token]
            props["chromaticity"] = float(colors[token].get("raw", {}).get("chromaticity", 0.0))
        nodes.append(
            {
                "id": f"function:{token}",
                "type": "function",
                "label": token,
                "props": props,
            }
        )
    output = Path(output_path).with_suffix(".json")
    output.parent.mkdir(parents=True, exist_ok=True)
    while True:
        payload = json.dumps(
            {"nodes": nodes, "edges": edges, "context": "global"}, separators=(",", ":")
        ).encode()
        if len(payload) <= MAX_BYTES:
            break
        if not edges:
            raise ValueError("Snapshot nodes exceed 500 KB")
        edges = edges[: max(0, len(edges) - 100)]
    output.write_bytes(payload)
