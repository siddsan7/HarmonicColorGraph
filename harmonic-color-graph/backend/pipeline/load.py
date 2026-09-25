"""F24: stream versioned Parquet artifacts into the private hcg graph schema.

The entire load and active-version switch share one transaction. An error in
COPY, validation, or ANALYZE rolls the staged version back and leaves the
previous active corpus untouched. Parquet is read in bounded record batches.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from psycopg import Connection, connect
from psycopg.types.json import Jsonb

from pipeline.manifest import Manifest

BATCH_ROWS = 4096
MAX_HCG_BYTES = 300 * 1024 * 1024
MAX_DATABASE_BYTES = 400 * 1024 * 1024
EDGE_TYPE_CODES = {
    "TRANSITIONS_TO": 1,
    "FUNCTIONS_AS": 2,
    "ABS_TRANSITIONS_TO": 3,
    "PATTERN_CONTAINS": 4,
    "HAS_ROOT": 5,
    "HAS_QUALITY": 6,
    "VOICE_LEADS_TO": 7,
}
# A contextual transition observed fewer than five times is too noisy for
# public graph traversal and would exhaust the 300 MB graph budget. Keep every
# global transition; predictive n-grams and source artifacts remain complete.
MIN_CONTEXT_EDGE_COUNT = 5
REQUIRED_ARTIFACTS = {
    "sections.parquet": "sections_analyzed",
    "transitions.parquet": "transitions_rows",
    "functions.parquet": "functions_rows",
    "abs_transitions.parquet": "abs_transitions_rows",
    "voice_leads.parquet": "voice_leads_rows",
    "ngrams.parquet": "ngrams_rows",
    "patterns.parquet": "patterns_rows",
    "pattern_examples.parquet": "pattern_examples_rows",
    "transition_examples.parquet": "transition_examples_rows",
    "song_refs.parquet": "song_refs_rows",
}
ARTIFACT_COLUMNS = {
    "sections.parquet": {"local_key", "genre", "section", "decade", "labels"},
    "transitions.parquet": {"context", "from_token", "to_token", "count", "prob", "pmi", "support"},
    "functions.parquet": {"chord", "mode", "token", "count"},
    "abs_transitions.parquet": {"from_chord", "to_chord", "count"},
    "voice_leads.parquet": {
        "from_chord",
        "to_chord",
        "total_motion",
        "max_voice_motion",
        "common_tones",
        "bass_motion",
        "parallel_perfects",
        "parsimonious",
    },
    "ngrams.parquet": {"context", "order", "history", "total", "distinct_next", "next", "cont"},
    "patterns.parquet": {
        "pattern",
        "length",
        "support",
        "song_count",
        "rotations_observed",
        "context_lifts",
    },
    "pattern_examples.parquet": {"pattern", "song_id", "section", "ordinal", "rank"},
    "transition_examples.parquet": {
        "from_token",
        "to_token",
        "song_id",
        "section",
        "ordinal",
        "rank",
    },
    "song_refs.parquet": {"song_id", "spotify_id", "genre", "decade"},
}

PITCH_CLASSES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
COLOR_AXES = (
    "tension",
    "stability",
    "chromaticity",
    "brightness",
    "surprise",
    "smoothness",
    "complexity",
    "resolution",
    "finality",
)


@dataclass
class LoadReport:
    version: str
    status: str
    active_version: str | None
    artifact_rows: dict[str, int] = field(default_factory=dict)
    table_rows: dict[str, int] = field(default_factory=dict)
    node_types: dict[str, int] = field(default_factory=dict)
    edge_types: dict[str, int] = field(default_factory=dict)
    hcg_size_bytes: int = 0
    database_size_bytes: int = 0


def _manifest_hash(payload: dict[str, Any]) -> str:
    normalized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _psycopg_url(db_url: str) -> str:
    """Accept the repository's SQLAlchemy URL as well as a native PG DSN."""
    return db_url.replace("postgresql+psycopg://", "postgresql://", 1)


def _json(text: str) -> Any:
    return json.loads(text)


def _artifact_batches(path: Path, columns: list[str] | None = None) -> Iterator[list[dict]]:
    import pyarrow.parquet as pq

    reader = pq.ParquetFile(path)
    for batch in reader.iter_batches(batch_size=BATCH_ROWS, columns=columns):
        yield batch.to_pylist()


def _artifact_rows(path: Path, columns: list[str] | None = None) -> Iterator[dict]:
    for batch in _artifact_batches(path, columns):
        yield from batch


def _artifact_content_hash(path: Path) -> str:
    """Reproduce ``content_hash`` without collecting a full corpus frame."""
    import polars as pl
    import pyarrow.parquet as pq

    digest = hashlib.sha256()
    for batch in pq.ParquetFile(path).iter_batches(batch_size=BATCH_ROWS):
        digest.update(pl.from_arrow(batch).write_ndjson().encode("utf-8"))
    return digest.hexdigest()


def _validate_artifacts(artifact_dir: Path, manifest: Manifest) -> dict[str, int]:
    import pyarrow.parquet as pq

    if not manifest.version or manifest.version != artifact_dir.name:
        raise ValueError("Manifest version must match the artifact directory")
    if not manifest.output_hashes:
        raise ValueError("Manifest has no output hashes")
    counts: dict[str, int] = {}
    for filename, manifest_key in REQUIRED_ARTIFACTS.items():
        path = artifact_dir / filename
        if not path.is_file() or filename not in manifest.output_hashes:
            raise ValueError(f"Missing completed pipeline artifact: {filename}")
        metadata = pq.ParquetFile(path).metadata
        columns = set(pq.ParquetFile(path).schema_arrow.names)
        missing = ARTIFACT_COLUMNS[filename] - columns
        if missing:
            raise ValueError(f"{filename} is missing columns: {sorted(missing)}")
        counts[filename] = metadata.num_rows
        expected = manifest.row_counts.get(manifest_key)
        if expected is not None and counts[filename] != expected:
            raise ValueError(f"{filename} has {counts[filename]} rows; manifest expects {expected}")
        if _artifact_content_hash(path) != manifest.output_hashes[filename]:
            raise ValueError(f"{filename} content hash does not match the manifest")
    budget = manifest.budget_estimate_mb.get("total")
    if budget is not None and budget > 300:
        raise ValueError(f"Manifest storage estimate {budget:.1f} MB exceeds 300 MB budget")
    return counts


def _node_id(kind: str, label: str) -> str:
    return f"{kind}:{label}"


def _chord_root_quality(symbol: str) -> tuple[str | None, str | None]:
    if ":" not in symbol:
        return None, None
    root, quality = symbol.split(":", 1)
    quality = quality.split("/", 1)[0]
    if not root or not quality:
        return None, None
    return root, quality


def _token_chromaticity(token: str) -> float:
    """Coarse graph fallback until F40 color profiles are available."""
    mode, _, figure = token.partition(":")
    if mode not in {"M", "m"} or not figure:
        return 0.5
    if figure.startswith(("b", "#")):
        return 0.8
    if "/" in figure:
        return 0.7
    match = re.match(r"^([ivIV]+)", figure)
    if not match:
        return 0.5
    degree = match.group(1)
    diatonic = (
        {"I", "ii", "iii", "IV", "V", "vi", "vii"}
        if mode == "M"
        else {"i", "ii", "III", "iv", "v", "VI", "VII"}
    )
    return 0.0 if degree in diatonic else 0.5


def _catalog(artifact_dir: Path) -> tuple[dict[str, tuple[str, str, dict]], set[str]]:
    """Collect only distinct node labels; rows remain streamed from Parquet."""
    nodes: dict[str, tuple[str, str, dict]] = {}
    contexts: set[str] = {"global"}

    def add(kind: str, label: str | None, props: dict | None = None) -> None:
        if label:
            if kind == "function" and props is None:
                props = {"chromaticity": _token_chromaticity(label)}
            nodes[_node_id(kind, label)] = (kind, label, props or {})

    for pitch in PITCH_CLASSES:
        add("pitch_class", pitch)
    for interval in range(12):
        add("interval", str(interval))
    for axis in COLOR_AXES:
        add("color_axis", axis)

    for row in _artifact_rows(
        artifact_dir / "sections.parquet",
        ["local_key", "genre", "section", "decade", "labels"],
    ):
        add("key", row["local_key"])
        add("genre", row["genre"])
        add("section", row["section"])
        add("era", row["decade"])
        for label in row["labels"] or []:
            add("relationship_type", label)

    def add_chord(symbol: str) -> None:
        add("chord", symbol)
        root, quality = _chord_root_quality(symbol)
        add("pitch_class", root)
        add("chord_quality", quality)

    for row in _artifact_rows(artifact_dir / "functions.parquet", ["chord", "token"]):
        add_chord(row["chord"])
        add("function", row["token"])
    for row in _artifact_rows(artifact_dir / "abs_transitions.parquet", ["from_chord", "to_chord"]):
        add_chord(row["from_chord"])
        add_chord(row["to_chord"])
    for row in _artifact_rows(
        artifact_dir / "transitions.parquet", ["context", "from_token", "to_token"]
    ):
        contexts.add(row["context"])
        add("function", row["from_token"])
        add("function", row["to_token"])
    for row in _artifact_rows(artifact_dir / "ngrams.parquet", ["context"]):
        contexts.add(row["context"])
    for row in _artifact_rows(artifact_dir / "patterns.parquet", ["pattern", "context_lifts"]):
        add("pattern", row["pattern"])
        for token in row["pattern"].split(" "):
            add("function", token)
        contexts.update(_json(row["context_lifts"]))
    return nodes, contexts


def _context_parts(key: str) -> tuple[str, str]:
    if key == "global":
        return "global", ""
    if ":" not in key:
        raise ValueError(f"Invalid context key: {key}")
    kind, value = key.split(":", 1)
    if kind not in {"genre", "section", "decade", "genre_section"} or not value:
        raise ValueError(f"Invalid context key: {key}")
    return kind, value


def _context_ids(conn: Connection, keys: set[str]) -> dict[str, int]:
    rows = conn.execute("select id, type, value from hcg.contexts order by id").fetchall()
    existing = {
        "global" if kind == "global" else f"{kind}:{value}": ident for ident, kind, value in rows
    }
    if "global" in existing and existing["global"] != 0:
        raise ValueError("Global context must use ID 0")
    if "global" not in existing:
        conn.execute(
            "insert into hcg.contexts (id, type, value, label) values (0, 'global', '', 'Global')"
        )
        existing["global"] = 0
    next_id = max(existing.values(), default=0) + 1
    for key in sorted(keys - existing.keys()):
        if next_id > 32767:
            raise ValueError("Context ID exceeds smallint range")
        kind, value = _context_parts(key)
        conn.execute(
            "insert into hcg.contexts (id, type, value, label) values (%s, %s, %s, %s)",
            (next_id, kind, value, value),
        )
        existing[key] = next_id
        next_id += 1
    return existing


def _copy_rows(
    conn: Connection,
    table: str,
    columns: tuple[str, ...],
    types: tuple[str, ...],
    rows: Iterable[tuple],
) -> int:
    """Binary COPY with explicit PG types, in bounded writes."""
    statement = f"COPY hcg.{table} ({', '.join(columns)}) FROM STDIN WITH (FORMAT BINARY)"
    count = 0
    with conn.cursor() as cursor, cursor.copy(statement) as copy:
        copy.set_types(types)
        for row in rows:
            copy.write_row(row)
            count += 1
    return count


def _edge_rows(artifact_dir: Path, version: str, contexts: dict[str, int], nodes: dict):
    transition_examples: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for example in _artifact_rows(artifact_dir / "transition_examples.parquet"):
        transition_examples[(example["from_token"], example["to_token"])].append(
            {
                "song_id": example["song_id"],
                "section": example["section"],
                "section_ordinal": example["ordinal"],
                "position": example.get("position"),
                "rank": example["rank"],
            }
        )
    for row in _artifact_rows(artifact_dir / "transitions.parquet"):
        global_edge = row["context"] == "global"
        fact_id = (
            f"transition:{row['from_token']}->{row['to_token']}:global" if global_edge else None
        )
        props = {"pmi": row["pmi"], "support": row["support"]}
        if fact_id:
            props["fact_ids"] = [fact_id]
            props["example_refs"] = transition_examples.get(
                (row["from_token"], row["to_token"]), []
            )
        yield (
            version,
            _node_id("function", row["from_token"]),
            _node_id("function", row["to_token"]),
            "TRANSITIONS_TO",
            contexts[row["context"]],
            row["count"],
            row["prob"],
            row["pmi"],
            Jsonb(props),
        )
    for row in _artifact_rows(artifact_dir / "functions.parquet"):
        yield (
            version,
            _node_id("chord", row["chord"]),
            _node_id("function", row["token"]),
            "FUNCTIONS_AS",
            0,
            row["count"],
            None,
            None,
            Jsonb({"mode": row["mode"]}),
        )
    for row in _artifact_rows(artifact_dir / "abs_transitions.parquet"):
        yield (
            version,
            _node_id("chord", row["from_chord"]),
            _node_id("chord", row["to_chord"]),
            "ABS_TRANSITIONS_TO",
            0,
            row["count"],
            None,
            None,
            Jsonb({}),
        )
    for row in _artifact_rows(artifact_dir / "voice_leads.parquet"):
        yield (
            version,
            _node_id("chord", row["from_chord"]),
            _node_id("chord", row["to_chord"]),
            "VOICE_LEADS_TO",
            0,
            None,
            None,
            row["total_motion"],
            Jsonb(
                {
                    "max_voice_motion": row["max_voice_motion"],
                    "common_tones": row["common_tones"],
                    "bass_motion": row["bass_motion"],
                    "parallel_perfects": row["parallel_perfects"],
                    "parsimonious": row["parsimonious"],
                }
            ),
        )
    for row in _artifact_rows(artifact_dir / "patterns.parquet", ["pattern"]):
        positions: dict[str, list[int]] = defaultdict(list)
        for index, token in enumerate(row["pattern"].split(" ")):
            positions[token].append(index)
        for token, indexes in positions.items():
            yield (
                version,
                _node_id("pattern", row["pattern"]),
                _node_id("function", token),
                "PATTERN_CONTAINS",
                0,
                None,
                None,
                None,
                Jsonb({"positions": indexes}),
            )
    for node_id, (kind, label, _) in nodes.items():
        if kind != "chord":
            continue
        root, quality = _chord_root_quality(label)
        for target_kind, target, edge_kind in (
            ("pitch_class", root, "HAS_ROOT"),
            ("chord_quality", quality, "HAS_QUALITY"),
        ):
            if target:
                yield (
                    version,
                    node_id,
                    _node_id(target_kind, target),
                    edge_kind,
                    0,
                    None,
                    None,
                    None,
                    Jsonb({}),
                )


def _compact_edge_rows(
    artifact_dir: Path,
    version: str,
    version_key: int,
    contexts: dict[str, int],
    nodes: dict,
    node_keys: dict[str, int],
) -> Iterator[tuple]:
    for _, src, dst, edge_type, context_id, count, prob, weight, wrapped_props in _edge_rows(
        artifact_dir, version, contexts, nodes
    ):
        if edge_type == "TRANSITIONS_TO" and context_id != 0 and count < MIN_CONTEXT_EDGE_COUNT:
            continue
        props = wrapped_props.obj
        support = props.get("support") if edge_type == "TRANSITIONS_TO" else None
        if edge_type == "TRANSITIONS_TO":
            # The high-cardinality edge rows store numeric values as compact
            # columns. Only global edges carry a small evidence payload.
            extra = {
                key: props[key]
                for key in ("fact_ids", "example_refs")
                if context_id == 0 and key in props
            }
        else:
            extra = props
        yield (
            version_key,
            node_keys[src],
            node_keys[dst],
            EDGE_TYPE_CODES[edge_type],
            context_id,
            count,
            prob,
            weight,
            support,
            Jsonb(extra) if extra else None,
        )


def _fact_rows(artifact_dir: Path, version: str) -> Iterator[tuple]:
    for row in _artifact_rows(artifact_dir / "transitions.parquet"):
        if row["context"] != "global":
            continue
        source, target = row["from_token"], row["to_token"]
        yield (
            f"transition:{source}->{target}:global",
            version,
            "transition",
            _node_id("function", source),
            "In the corpus, {from_token} moves to {to_token} with probability {probability}.",
            Jsonb(
                {
                    "from_token": source,
                    "to_token": target,
                    "probability": row["prob"],
                    "count": row["count"],
                }
            ),
        )


def _table_counts(conn: Connection, version: str) -> dict[str, int]:
    tables = (
        "nodes",
        "ngram_histories",
        "ngram_discount_stats",
        "patterns",
        "song_refs",
        "pattern_examples",
        "transition_examples",
        "relationship_types",
        "facts",
    )
    counts = {
        table: conn.execute(
            f"select count(*) from hcg.{table} where version = %s", (version,)
        ).fetchone()[0]
        for table in tables
    }
    counts["edges"] = conn.execute(
        """select count(*) from hcg.edges_compact
           where version_key = (select version_key from hcg.corpus_versions where version = %s)""",
        (version,),
    ).fetchone()[0]
    return counts


def _populate_ngram_discount_stats(conn: Connection, version: str) -> None:
    """Materialize KN discounts inside the loader's atomic transaction.

    This scan is allowed the loader's long timeout; the API performs only
    bounded primary-key reads from the result. Rows are version-scoped and
    cascade away when an old corpus version is explicitly pruned.
    """
    conn.execute(
        """insert into hcg.ngram_discount_stats (version, context_id, ord, n1, n2)
           select h.version, h.context_id, h.ord,
                  count(*) filter (where kv.value::integer = 1),
                  count(*) filter (where kv.value::integer = 2)
           from hcg.ngram_histories h
           cross join lateral jsonb_each_text(h.next) kv
           where h.version = %s and h.ord > 1
           group by h.version, h.context_id, h.ord""",
        (version,),
    )


def _size_report(conn: Connection) -> tuple[int, int]:
    hcg_bytes = conn.execute(
        """select coalesce(sum(pg_total_relation_size(c.oid)), 0)
           from pg_class c join pg_namespace n on n.oid = c.relnamespace
          where n.nspname = 'hcg' and c.relkind in ('r', 'm')"""
    ).fetchone()[0]
    database_bytes = conn.execute("select pg_database_size(current_database())").fetchone()[0]
    return hcg_bytes, database_bytes


def load_corpus(artifact_dir: str | Path, db_url: str) -> LoadReport:
    artifact_dir = Path(artifact_dir)
    manifest_path = artifact_dir / "manifest.json"
    manifest = Manifest.read(manifest_path)
    artifact_counts = _validate_artifacts(artifact_dir, manifest)
    payload = manifest.to_dict()
    version = manifest.version
    manifest_digest = _manifest_hash(payload)

    with connect(_psycopg_url(db_url)) as conn:
        with conn.transaction():
            # Direct Supabase roles default to a two-minute statement timeout;
            # binary COPY of the complete graph can legitimately take longer.
            conn.execute("set local statement_timeout = '20min'")
            conn.execute("select pg_advisory_xact_lock(hashtext('hcg.corpus_loader'))")
            current = conn.execute(
                "select manifest, active from hcg.corpus_versions where version = %s for update",
                (version,),
            ).fetchone()
            if current:
                if _manifest_hash(current[0]) != manifest_digest:
                    raise ValueError(f"Version {version} already exists with a different manifest")
                if not current[1]:
                    hcg_size, db_size = _size_report(conn)
                    if hcg_size > MAX_HCG_BYTES or db_size > MAX_DATABASE_BYTES:
                        raise ValueError("Database exceeds storage gate before reactivation")
                    conn.execute("update hcg.corpus_versions set active = false where active")
                    conn.execute(
                        "update hcg.corpus_versions set active = true where version = %s",
                        (version,),
                    )
                    status = "reactivated"
                else:
                    status = "no-op"
            else:
                nodes, context_keys = _catalog(artifact_dir)
                version_key = conn.execute(
                    "insert into hcg.corpus_versions (version, manifest, active) "
                    "values (%s, %s, false) returning version_key",
                    (version, Jsonb(payload)),
                ).fetchone()[0]
                contexts = _context_ids(conn, context_keys)
                _copy_rows(
                    conn,
                    "nodes",
                    ("version", "id", "type", "label", "props"),
                    ("text", "text", "text", "text", "jsonb"),
                    (
                        (version, node_id, kind, label, Jsonb(props))
                        for node_id, (kind, label, props) in sorted(nodes.items())
                    ),
                )
                node_keys = dict(
                    conn.execute(
                        "select id, node_key from hcg.nodes where version = %s", (version,)
                    ).fetchall()
                )
                _copy_rows(
                    conn,
                    "edges_compact",
                    (
                        "version_key",
                        "src_key",
                        "dst_key",
                        "type_code",
                        "context_id",
                        "count",
                        "prob",
                        "weight",
                        "support",
                        "props",
                    ),
                    (
                        "int2",
                        "int4",
                        "int4",
                        "int2",
                        "int2",
                        "int4",
                        "float4",
                        "float4",
                        "int4",
                        "jsonb",
                    ),
                    _compact_edge_rows(
                        artifact_dir, version, version_key, contexts, nodes, node_keys
                    ),
                )
                _copy_rows(
                    conn,
                    "ngram_histories",
                    (
                        "version",
                        "context_id",
                        "ord",
                        "history",
                        "total",
                        "distinct_next",
                        "next",
                        "cont",
                    ),
                    ("text", "int2", "int2", "text", "int4", "int4", "jsonb", "jsonb"),
                    (
                        (
                            version,
                            contexts[r["context"]],
                            r["order"],
                            r["history"],
                            r["total"],
                            r["distinct_next"],
                            Jsonb(_json(r["next"])),
                            Jsonb(_json(r["cont"])),
                        )
                        for r in _artifact_rows(artifact_dir / "ngrams.parquet")
                    ),
                )
                _populate_ngram_discount_stats(conn, version)
                _copy_rows(
                    conn,
                    "patterns",
                    (
                        "version",
                        "pattern",
                        "length",
                        "support",
                        "song_count",
                        "rotations_observed",
                        "context_lifts",
                    ),
                    ("text", "text", "int2", "int4", "int4", "int2[]", "jsonb"),
                    (
                        (
                            version,
                            r["pattern"],
                            r["length"],
                            r["support"],
                            r["song_count"],
                            r["rotations_observed"],
                            Jsonb(_json(r["context_lifts"])),
                        )
                        for r in _artifact_rows(artifact_dir / "patterns.parquet")
                    ),
                )
                _copy_rows(
                    conn,
                    "song_refs",
                    ("version", "song_id", "spotify_id", "genre", "decade"),
                    ("text", "text", "text", "text", "text"),
                    (
                        (version, r["song_id"], r["spotify_id"], r["genre"], r["decade"])
                        for r in _artifact_rows(artifact_dir / "song_refs.parquet")
                    ),
                )
                _copy_rows(
                    conn,
                    "pattern_examples",
                    ("version", "pattern", "song_id", "section", "ordinal", "position", "rank"),
                    ("text", "text", "text", "text", "int4", "int4", "int2"),
                    (
                        (
                            version,
                            r["pattern"],
                            r["song_id"],
                            r["section"],
                            r["ordinal"],
                            r.get("position"),
                            r["rank"],
                        )
                        for r in _artifact_rows(artifact_dir / "pattern_examples.parquet")
                    ),
                )
                _copy_rows(
                    conn,
                    "transition_examples",
                    (
                        "version",
                        "from_token",
                        "to_token",
                        "song_id",
                        "section",
                        "ordinal",
                        "position",
                        "rank",
                    ),
                    ("text", "text", "text", "text", "text", "int4", "int4", "int2"),
                    (
                        (
                            version,
                            r["from_token"],
                            r["to_token"],
                            r["song_id"],
                            r["section"],
                            r["ordinal"],
                            r.get("position"),
                            r["rank"],
                        )
                        for r in _artifact_rows(artifact_dir / "transition_examples.parquet")
                    ),
                )
                _copy_rows(
                    conn,
                    "relationship_types",
                    ("version", "id", "label", "props"),
                    ("text", "text", "text", "jsonb"),
                    (
                        (version, label, label, Jsonb({}))
                        for _, (kind, label, _) in sorted(nodes.items())
                        if kind == "relationship_type"
                    ),
                )
                _copy_rows(
                    conn,
                    "facts",
                    ("fact_id", "version", "kind", "subject", "template", "params"),
                    ("text", "text", "text", "text", "text", "jsonb"),
                    _fact_rows(artifact_dir, version),
                )
                table_counts = _table_counts(conn, version)
                expected = {
                    "ngram_histories": artifact_counts["ngrams.parquet"],
                    "patterns": artifact_counts["patterns.parquet"],
                    "song_refs": artifact_counts["song_refs.parquet"],
                    "pattern_examples": artifact_counts["pattern_examples.parquet"],
                    "transition_examples": artifact_counts["transition_examples.parquet"],
                }
                for table, count in expected.items():
                    if table_counts[table] != count:
                        raise ValueError(
                            f"{table}: loaded {table_counts[table]} rows; expected {count}"
                        )
                edge_counts = dict(
                    conn.execute(
                        "select type_code, count(*) from hcg.edges_compact "
                        "where version_key = %s group by type_code",
                        (version_key,),
                    ).fetchall()
                )
                retained_transitions = sum(
                    1
                    for row in _artifact_rows(
                        artifact_dir / "transitions.parquet", ["context", "count"]
                    )
                    if row["context"] == "global" or row["count"] >= MIN_CONTEXT_EDGE_COUNT
                )
                for edge_type, artifact in (
                    ("TRANSITIONS_TO", "transitions.parquet"),
                    ("FUNCTIONS_AS", "functions.parquet"),
                    ("ABS_TRANSITIONS_TO", "abs_transitions.parquet"),
                ):
                    expected_count = (
                        retained_transitions
                        if edge_type == "TRANSITIONS_TO"
                        else artifact_counts[artifact]
                    )
                    if edge_counts.get(EDGE_TYPE_CODES[edge_type], 0) != expected_count:
                        raise ValueError(f"{edge_type} count differs from {artifact}")
                if table_counts["nodes"] != len(nodes):
                    raise ValueError("Loaded node count differs from the artifact-derived catalog")
                for table in (
                    "nodes",
                    "edges_compact",
                    "ngram_histories",
                    "ngram_discount_stats",
                    "patterns",
                    "song_refs",
                    "pattern_examples",
                    "transition_examples",
                    "relationship_types",
                    "facts",
                ):
                    conn.execute(f"analyze hcg.{table}")
                hcg_size, db_size = _size_report(conn)
                if hcg_size > MAX_HCG_BYTES or db_size > MAX_DATABASE_BYTES:
                    raise ValueError(
                        "Load exceeds storage gate before activation: "
                        f"hcg={hcg_size / 1048576:.1f} MB (limit 300), "
                        f"database={db_size / 1048576:.1f} MB (limit 400)"
                    )
                conn.execute("update hcg.corpus_versions set active = false where active")
                conn.execute(
                    "update hcg.corpus_versions set active = true where version = %s", (version,)
                )
                status = "loaded"

            active = conn.execute("select hcg.v()").fetchone()[0]
            table_counts = _table_counts(conn, version)
            node_types = dict(
                conn.execute(
                    "select type, count(*) from hcg.nodes where version = %s group by type",
                    (version,),
                ).fetchall()
            )
            edge_types = dict(
                conn.execute(
                    "select type_code, count(*) from hcg.edges_compact "
                    "where version_key = (select version_key from hcg.corpus_versions "
                    "where version = %s) group by type_code",
                    (version,),
                ).fetchall()
            )
            edge_types = {
                name: edge_types.get(code, 0)
                for name, code in EDGE_TYPE_CODES.items()
                if edge_types.get(code, 0)
            }
            hcg_size, db_size = _size_report(conn)
            return LoadReport(
                version=version,
                status=status,
                active_version=active,
                artifact_rows=artifact_counts,
                table_rows=table_counts,
                node_types=node_types,
                edge_types=edge_types,
                hcg_size_bytes=hcg_size,
                database_size_bytes=db_size,
            )


def garbage_collect(db_url: str, *, confirm: bool = False) -> list[str]:
    """Delete inactive versions only after an explicit CLI confirmation."""
    if not confirm:
        raise ValueError("Garbage collection requires explicit confirmation")
    with connect(_psycopg_url(db_url)) as conn, conn.transaction():
        conn.execute("select pg_advisory_xact_lock(hashtext('hcg.corpus_loader'))")
        versions = [
            r[0]
            for r in conn.execute(
                "select version from hcg.corpus_versions where not active order by version"
            ).fetchall()
        ]
        for version in versions:
            conn.execute(
                "delete from hcg.corpus_versions where version = %s and not active", (version,)
            )
    return versions
