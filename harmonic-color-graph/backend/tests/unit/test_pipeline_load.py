"""F24 artifact mapping and versioned loader checks."""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

import pytest
from psycopg.types.json import Jsonb

pl = pytest.importorskip("polars")
pytest.importorskip("pyarrow")

from pipeline.load import (  # noqa: E402
    _catalog,
    _compact_edge_rows,
    _context_parts,
    _edge_rows,
    _fact_rows,
    _psycopg_url,
    _validate_artifacts,
    load_corpus,
)
from pipeline.manifest import Manifest, content_hash  # noqa: E402


@pytest.fixture
def artifact_dir(tmp_path: Path) -> Path:
    path = tmp_path / "cv-f24-unit"
    path.mkdir()
    frames = {
        "sections.parquet": pl.DataFrame(
            {
                "local_key": ["C major"],
                "genre": ["pop"],
                "section": ["chorus"],
                "decade": ["2020s"],
                "labels": [["authentic_cadence"]],
            }
        ),
        "transitions.parquet": pl.DataFrame(
            {
                "context": ["global"],
                "from_token": ["M:V"],
                "to_token": ["M:I"],
                "count": [3],
                "prob": [1.0],
                "pmi": [0.0],
                "support": [1],
            }
        ),
        "functions.parquet": pl.DataFrame(
            {
                "chord": ["G:maj", "C:maj"],
                "mode": ["major", "major"],
                "token": ["M:V", "M:I"],
                "count": [3, 3],
            }
        ),
        "abs_transitions.parquet": pl.DataFrame(
            {
                "from_chord": ["G:maj"],
                "to_chord": ["C:maj"],
                "count": [3],
            }
        ),
        "voice_leads.parquet": pl.DataFrame(
            {
                "from_chord": ["G:maj"],
                "to_chord": ["C:maj"],
                "total_motion": [8],
                "max_voice_motion": [5],
                "common_tones": [1],
                "bass_motion": [5],
                "parallel_perfects": [0],
                "parsimonious": [None],
            },
            schema={
                "from_chord": pl.Utf8,
                "to_chord": pl.Utf8,
                "total_motion": pl.Int64,
                "max_voice_motion": pl.Int64,
                "common_tones": pl.Int64,
                "bass_motion": pl.Int64,
                "parallel_perfects": pl.Int64,
                "parsimonious": pl.Utf8,
            },
        ),
        "ngrams.parquet": pl.DataFrame(
            {
                "context": ["global"],
                "order": [2],
                "history": ["M:V"],
                "total": [3],
                "distinct_next": [1],
                "next": ['{"M:I": 3}'],
                "cont": ["{}"],
            }
        ),
        "patterns.parquet": pl.DataFrame(
            {
                "pattern": ["M:I M:V M:I"],
                "length": [3],
                "support": [1],
                "song_count": [1],
                "rotations_observed": [[0]],
                "context_lifts": ["{}"],
            }
        ),
        "pattern_examples.parquet": pl.DataFrame(
            {
                "pattern": ["M:I M:V M:I"],
                "song_id": ["song-1"],
                "section": ["chorus"],
                "ordinal": [1],
                "position": [0],
                "rank": [1],
            }
        ),
        "transition_examples.parquet": pl.DataFrame(
            {
                "from_token": ["M:V"],
                "to_token": ["M:I"],
                "song_id": ["song-1"],
                "section": ["chorus"],
                "ordinal": [1],
                "position": [1],
                "rank": [1],
            }
        ),
        "song_refs.parquet": pl.DataFrame(
            {
                "song_id": ["song-1"],
                "spotify_id": [None],
                "genre": ["pop"],
                "decade": ["2020s"],
            }
        ),
        "color.parquet": pl.DataFrame(
            {
                "axis": ["tension"],
                "subject_type": ["transition"],
                "count": [1],
                "p05": [0.1],
                "p25": [0.2],
                "p50": [0.3],
                "p75": [0.4],
                "p95": [0.5],
                "mean": [0.3],
                "std": [0.1],
            }
        ),
        "color_profiles.parquet": pl.DataFrame(
            {
                "subject_type": ["function", "transition", "pattern"],
                "subject_id": ["M:I", "M:V>M:I", "M:I M:V M:I"],
                "mode": ["major", "major", "major"],
                "support": [3, 3, 1],
                "axes": ['{"raw": {}}', '{"raw": {}}', '{"raw": {}}'],
            }
        ),
        "embeddings.parquet": pl.DataFrame(
            {
                "subject_type": ["function", "function", "pattern"],
                "subject_id": ["M:V", "M:I", "M:I M:V M:I"],
                "model": ["chord2vec", "chord2vec", "chord2vec"],
                "vec": [
                    [1.0] + [0.0] * 63,
                    [0.0, 1.0] + [0.0] * 62,
                    [0.6, 0.8] + [0.0] * 62,
                ],
            }
        ),
    }
    manifest = Manifest(version=path.name, source_path="fixture", source_sha256="fixture")
    manifest.row_counts = {
        "sections_analyzed": 1,
        "transitions_rows": 1,
        "functions_rows": 2,
        "abs_transitions_rows": 1,
        "voice_leads_rows": 1,
        "ngrams_rows": 1,
        "patterns_rows": 1,
        "pattern_examples_rows": 1,
        "transition_examples_rows": 1,
        "song_refs_rows": 1,
        "color_norms_rows": 1,
        "color_profiles_rows": 3,
        "embeddings_rows": 3,
    }
    manifest.params["embedding_default_model"] = "chord2vec"
    for filename, frame in frames.items():
        frame.write_parquet(path / filename)
        manifest.output_hashes[filename] = content_hash(frame)
    manifest.write(path / "manifest.json")
    return path


def test_catalog_maps_artifact_columns_to_prefixed_graph_ids(artifact_dir: Path):
    manifest = Manifest.read(artifact_dir / "manifest.json")
    counts = _validate_artifacts(artifact_dir, manifest)
    assert counts["functions.parquet"] == 2
    assert counts["embeddings.parquet"] == 3
    nodes, contexts = _catalog(artifact_dir)
    assert {
        "function:M:V",
        "function:M:I",
        "chord:G:maj",
        "chord:C:maj",
        "pattern:M:I M:V M:I",
        "relationship_type:authentic_cadence",
    } <= nodes.keys()
    assert contexts == {"global"}
    assert nodes["function:M:V"][2]["chromaticity"] == 0.0
    edges = list(_edge_rows(artifact_dir, manifest.version, {"global": 0}, nodes))
    kinds = [edge[3] for edge in edges]
    assert kinds.count("TRANSITIONS_TO") == 1
    assert kinds.count("FUNCTIONS_AS") == 2
    assert kinds.count("ABS_TRANSITIONS_TO") == 1
    assert kinds.count("VOICE_LEADS_TO") == 1
    assert kinds.count("PATTERN_CONTAINS") == 2
    assert ("HAS_ROOT" in kinds) and ("HAS_QUALITY" in kinds)
    transition = next(edge for edge in edges if edge[3] == "TRANSITIONS_TO")
    assert transition[1:5] == ("function:M:V", "function:M:I", "TRANSITIONS_TO", 0)
    assert transition[8].obj["fact_ids"] == ["transition:M:V->M:I:global"]
    assert transition[8].obj["example_refs"][0]["position"] == 1
    voice_leads = next(edge for edge in edges if edge[3] == "VOICE_LEADS_TO")
    assert voice_leads[1:5] == ("chord:G:maj", "chord:C:maj", "VOICE_LEADS_TO", 0)
    assert voice_leads[7] == 8  # weight carries total_motion.
    assert voice_leads[8].obj == {
        "max_voice_motion": 5,
        "common_tones": 1,
        "bass_motion": 5,
        "parallel_perfects": 0,
        "parsimonious": None,
    }
    compact = list(
        _compact_edge_rows(
            artifact_dir,
            manifest.version,
            7,
            {"global": 0},
            nodes,
            {node_id: index for index, node_id in enumerate(sorted(nodes), 1)},
        )
    )
    transition_compact = next(edge for edge in compact if edge[3] == 1)
    assert transition_compact[:1] == (7,)
    assert transition_compact[8] == 1  # Numeric support replaces repeated JSON.
    assert transition_compact[9].obj["fact_ids"] == ["transition:M:V->M:I:global"]
    voice_leads_compact = next(edge for edge in compact if edge[3] == 7)
    assert voice_leads_compact[7] == 8  # weight carries total_motion.
    assert voice_leads_compact[9].obj["common_tones"] == 1
    fact = next(_fact_rows(artifact_dir, manifest.version))
    assert fact[:4] == (
        "transition:M:V->M:I:global",
        manifest.version,
        "transition",
        "function:M:V",
    )


def test_manifest_count_mismatch_blocks_load_before_db(artifact_dir: Path):
    manifest_path = artifact_dir / "manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["row_counts"]["patterns_rows"] = 2
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="patterns.parquet has 1 rows"):
        _validate_artifacts(artifact_dir, Manifest.read(manifest_path))


def test_compact_edge_loader_prunes_unsupported_contexts_but_keeps_global(monkeypatch):
    raw = [
        ("cv-test", "a", "b", "TRANSITIONS_TO", 0, 1, 0.5, 0.0, Jsonb({"support": 1})),
        ("cv-test", "a", "b", "TRANSITIONS_TO", 1, 4, 0.5, 0.0, Jsonb({"support": 4})),
        ("cv-test", "a", "b", "TRANSITIONS_TO", 1, 5, 0.5, 0.0, Jsonb({"support": 5})),
    ]
    monkeypatch.setattr("pipeline.load._edge_rows", lambda *args: iter(raw))
    retained = list(_compact_edge_rows(Path("."), "cv-test", 1, {}, {}, {"a": 1, "b": 2}))
    assert [(row[4], row[5]) for row in retained] == [(0, 1), (1, 5)]


def test_streamed_hash_detects_artifact_change(artifact_dir: Path, monkeypatch):
    import pipeline.load as loader

    monkeypatch.setattr(loader, "BATCH_ROWS", 1)
    manifest = Manifest.read(artifact_dir / "manifest.json")
    _validate_artifacts(artifact_dir, manifest)
    path = artifact_dir / "functions.parquet"
    frame = pl.read_parquet(path)
    frame.with_columns(
        pl.when(pl.col("chord") == "G:maj")
        .then(pl.lit("G:min"))
        .otherwise(pl.col("chord"))
        .alias("chord")
    ).write_parquet(path)
    with pytest.raises(ValueError, match="content hash does not match"):
        _validate_artifacts(artifact_dir, manifest)


def test_context_key_validation():
    assert _context_parts("global") == ("global", "")
    assert _context_parts("genre_section:pop:chorus") == ("genre_section", "pop:chorus")
    with pytest.raises(ValueError, match="Invalid context key"):
        _context_parts("other:value")
    assert _psycopg_url("postgresql+psycopg://host/db") == "postgresql://host/db"


@pytest.mark.pg
@pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="TEST_DATABASE_URL is not set")
def test_loader_activates_once_and_preserves_previous_on_failed_stage(
    artifact_dir: Path, monkeypatch
):
    import psycopg

    import pipeline.load as loader

    db_url = os.environ["TEST_DATABASE_URL"]
    native_db_url = loader._psycopg_url(db_url)
    version = artifact_dir.name
    failed_version = f"{version}-failed"
    with psycopg.connect(native_db_url) as conn:
        previous = conn.execute("select hcg.v()").fetchone()[0]
    try:
        first = load_corpus(artifact_dir, db_url)
        assert first.status == "loaded"
        assert first.active_version == version
        assert first.edge_types["TRANSITIONS_TO"] == 1
        assert first.edge_types["VOICE_LEADS_TO"] == 1
        assert first.edge_types["SIMILAR_TO"] == 2
        assert first.table_rows["embeddings"] == 3
        assert first.table_rows["patterns"] == 1
        second = load_corpus(artifact_dir, db_url)
        assert second.status == "no-op"

        changed = json.loads((artifact_dir / "manifest.json").read_text(encoding="utf-8"))
        changed["params"]["changed"] = True
        (artifact_dir / "manifest.json").write_text(json.dumps(changed), encoding="utf-8")
        with pytest.raises(ValueError, match="different manifest"):
            load_corpus(artifact_dir, db_url)
        with psycopg.connect(native_db_url) as conn:
            assert conn.execute("select hcg.v()").fetchone()[0] == version

        failed_dir = artifact_dir.parent / failed_version
        shutil.copytree(artifact_dir, failed_dir)
        failed_manifest_path = failed_dir / "manifest.json"
        failed_manifest = json.loads(failed_manifest_path.read_text(encoding="utf-8"))
        failed_manifest["version"] = failed_version
        failed_manifest_path.write_text(json.dumps(failed_manifest), encoding="utf-8")

        def fail_facts(_artifact_dir, _version):
            raise RuntimeError("injected failure after preceding COPY tables")
            yield  # pragma: no cover - make this a generator like _fact_rows

        monkeypatch.setattr(loader, "_fact_rows", fail_facts)
        with pytest.raises(RuntimeError, match="injected failure"):
            load_corpus(failed_dir, db_url)
        with psycopg.connect(native_db_url) as conn:
            assert conn.execute("select hcg.v()").fetchone()[0] == version
            assert (
                conn.execute(
                    "select count(*) from hcg.corpus_versions where version = %s", (failed_version,)
                ).fetchone()[0]
                == 0
            )
    finally:
        with psycopg.connect(native_db_url) as conn:
            with conn.transaction():
                conn.execute("update hcg.corpus_versions set active = false where active")
                conn.execute(
                    "delete from hcg.corpus_versions where version in (%s, %s)",
                    (version, failed_version),
                )
                if previous:
                    conn.execute(
                        "update hcg.corpus_versions set active = true where version = %s",
                        (previous,),
                    )
