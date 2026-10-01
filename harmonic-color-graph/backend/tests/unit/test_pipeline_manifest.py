"""Streaming hashes retain compatibility with published corpus manifests."""

import pytest

pl = pytest.importorskip("polars")
pytest.importorskip("pyarrow")

from pipeline.manifest import Manifest, content_hash, parquet_content_hash  # noqa: E402


@pytest.mark.parametrize("batch_size", [1, 2, 7, 4096])
@pytest.mark.parametrize("empty", [False, True])
def test_parquet_hash_matches_existing_nested_unicode_content(tmp_path, batch_size, empty):
    frame = pl.DataFrame(
        {
            "section": ["refrain ♭", None, "", "verse"],
            "tokens": [["M:I", "M:V7"], [], None, ["m:i"]],
            "confidence": [0.123456789, None, 1.0, 1e-10],
            "ambiguous": [False, True, None, False],
        }
    )
    if empty:
        frame = frame.head(0)
    path = tmp_path / "sections.parquet"
    frame.write_parquet(path, row_group_size=2)
    assert parquet_content_hash(path, batch_size) == content_hash(frame)


def test_parquet_hash_rejects_invalid_batch_size(tmp_path):
    with pytest.raises(ValueError, match="batch_size"):
        parquet_content_hash(tmp_path / "unused.parquet", 0)


def test_interrupted_manifest_replacement_preserves_previous_checkpoint(tmp_path, monkeypatch):
    path = tmp_path / "manifest.json"
    manifest = Manifest(version="cv-old", source_path="source", source_sha256="hash")
    manifest.write(path)
    before = path.read_bytes()
    manifest.version = "cv-new"

    def fail_replace(*_args):
        raise OSError("injected replacement failure")

    monkeypatch.setattr("pipeline.manifest.os.replace", fail_replace)
    with pytest.raises(OSError, match="injected"):
        manifest.write(path)
    assert path.read_bytes() == before
    assert list(tmp_path.iterdir()) == [path]
