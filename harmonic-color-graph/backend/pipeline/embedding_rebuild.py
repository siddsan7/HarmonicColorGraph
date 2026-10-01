"""Prepare immutable embedding artifacts without activating or reloading a corpus."""

from __future__ import annotations

import json
import shutil
import tempfile
from dataclasses import asdict
from pathlib import Path
from uuid import uuid4

from pipeline.manifest import sha256_file
from pipeline.memory_guard import MemoryGuard


def prepare_embedding_rebuild(root: Path, version: str, progress) -> dict:
    from pipeline.embedding_eval import evaluate_embeddings
    from pipeline.projection_export import export_projection
    from pipeline.stages.embeddings import run_embeddings

    root = root.resolve()
    source = (root / version).resolve()
    if source.parent != root or source.name != version or not source.is_dir():
        raise FileNotFoundError("Corpus artifacts are not available for this version")
    inputs = {}
    for name in ("sections.parquet", "transitions.parquet", "patterns.parquet"):
        path = (source / name).resolve()
        if path.parent != source or not path.is_file():
            raise FileNotFoundError(f"Embedding input is unavailable: {name}")
        inputs[name] = path
    # Publish only a complete bundle. A failed/retried build cannot overwrite
    # the source corpus or a previously completed bundle.
    rebuild_root = (root / "embedding-rebuilds").resolve()
    if rebuild_root.parent != root:
        raise ValueError("Embedding output must remain inside the artifact root")
    rebuild_root.mkdir(exist_ok=True)
    build_id = f"{version}-{uuid4().hex}"
    destination = rebuild_root / build_id
    progress(0.05, "preparing_embedding_inputs", 0, 3)
    with tempfile.TemporaryDirectory(prefix=".building-", dir=rebuild_root) as temp:
        staging = Path(temp)
        hashes = {}
        for index, (name, path) in enumerate(inputs.items(), 1):
            # Copying inputs also isolates a build from later source edits.
            shutil.copyfile(path, staging / name)
            hashes[name] = sha256_file(staging / name)
            progress(0.05 + index * 0.05, "preparing_embedding_inputs", index, 3)
        with MemoryGuard(label="embedding_rebuild"):
            progress(0.25, "training_embeddings", None, None)
            summary = run_embeddings(staging / "sections.parquet", staging)
            progress(0.75, "evaluating_embeddings", None, None)
            evaluations, default_model = evaluate_embeddings(staging / "embeddings.parquet")
            export_projection(
                staging / "embedding_projection.parquet", staging / "embedding-map.json"
            )
        outputs = ("embeddings.parquet", "embedding_projection.parquet", "embedding-map.json")
        report = {
            "corpus_version": version,
            "artifact_bundle": f"embedding-rebuilds/{build_id}",
            "activation_required": True,
            "summary": asdict(summary),
            "default_model": default_model,
            "evaluations": [asdict(item) for item in evaluations],
            "source_sha256": hashes,
            "output_sha256": {name: sha256_file(staging / name) for name in outputs},
        }
        (staging / "rebuild.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        # Inputs are reproducible from their source hashes and need not be
        # duplicated permanently in every completed output bundle.
        for name in inputs:
            (staging / name).unlink()
        staging.rename(destination)
    progress(0.95, "embedding_artifacts_ready", summary.rows_written, summary.rows_written)
    return report
