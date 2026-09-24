"""Build manifest: provenance, params, timings, and output hashes for a
versioned pipeline run (F20)."""

from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

LICENSE = "CC BY-NC 4.0"
CITATION = "Chordonomicon (Kantarelis et al., 2024), CC BY-NC 4.0"


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def content_hash(df) -> str:  # noqa: ANN001 - polars.DataFrame, kept untyped to avoid a hard import
    """A row/column-content hash independent of parquet's own file metadata
    (compression, writer version), so it stays stable across runs that
    produce byte-different but data-identical files. Callers must write
    `df` in a deterministic row order before hashing. Uses NDJSON, not CSV,
    because CSV can't represent the list columns some pipeline outputs have.
    """
    return sha256_text(df.write_ndjson())


# hcg.edges/hcg.ngram_histories/hcg.patterns' own btree indexes: a rough
# multiplier for index overhead on top of raw row bytes.
INDEX_OVERHEAD_FACTOR = 1.4


def measured_table_mb(df, text_columns: list[str], fixed_bytes_per_row: int = 0) -> float:  # noqa: ANN001
    """Budget estimate from *actual* column byte lengths, not a guess --
    needed for tables with variable-length JSON/text columns (ngrams'
    `next`/`cont`, patterns' `context_lifts`) where a fixed per-column
    guess would be wildly off depending on real content.
    """
    if df.height == 0:
        return 0.0
    text_bytes_per_row = sum(df[column].str.len_bytes().mean() or 0 for column in text_columns)
    bytes_per_row = text_bytes_per_row + fixed_bytes_per_row
    return (df.height * bytes_per_row * INDEX_OVERHEAD_FACTOR) / (1024 * 1024)


def git_sha(repo_root: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout.strip() or None


@dataclass
class Manifest:
    version: str
    source_path: str
    source_sha256: str
    row_counts: dict[str, int] = field(default_factory=dict)
    license: str = LICENSE
    citation: str = CITATION
    git_sha: str | None = None
    params: dict = field(default_factory=dict)
    stage_timings_s: dict[str, float] = field(default_factory=dict)
    output_hashes: dict[str, str] = field(default_factory=dict)
    budget_estimate_mb: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "source_path": self.source_path,
            "source_sha256": self.source_sha256,
            "row_counts": self.row_counts,
            "license": self.license,
            "citation": self.citation,
            "git_sha": self.git_sha,
            "params": self.params,
            "stage_timings_s": self.stage_timings_s,
            "output_hashes": self.output_hashes,
            "budget_estimate_mb": self.budget_estimate_mb,
        }

    def write(self, path: str | Path) -> None:
        Path(path).write_text(
            json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    @classmethod
    def read(cls, path: str | Path) -> Manifest:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(
            version=payload["version"],
            source_path=payload["source_path"],
            source_sha256=payload["source_sha256"],
            row_counts=payload.get("row_counts", {}),
            license=payload.get("license", LICENSE),
            citation=payload.get("citation", CITATION),
            git_sha=payload.get("git_sha"),
            params=payload.get("params", {}),
            stage_timings_s=payload.get("stage_timings_s", {}),
            output_hashes=payload.get("output_hashes", {}),
            budget_estimate_mb=payload.get("budget_estimate_mb", {}),
        )
