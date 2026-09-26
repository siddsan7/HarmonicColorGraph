"""Check active documentation links and the immutable plan split archive."""
from pathlib import Path
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[1]
FILES = ["AGENTS.md", "context/HANDOFF.md", "context/progress-tracker.md",
         "context/docs-index.md", "context/ai-workflow-rules.md",
         "feature-specs/v2-implementation-plan.md"]


def check():
    errors = []
    for name in FILES:
        path = ROOT / name
        body = path.read_text(encoding="utf-8")
        for link in re.findall(r"\]\(([^)]+)\)", body):
            if "://" in link or link.startswith("#"):
                continue
            target = (path.parent / link.split("#")[0]).resolve()
            if not target.is_relative_to(ROOT) or not target.exists():
                errors.append(f"{name}: missing local link {link}")
    manifest_path = ROOT / "feature-specs/v2/split-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    archive = (manifest_path.parent / manifest["archive"]).read_bytes()
    if hashlib.sha256(archive).hexdigest() != manifest["original_sha256"]:
        errors.append("Immutable original plan checksum changed")
    # Milestone text may evolve after the split; assert all original IDs survive.
    active = b"".join((manifest_path.parent / p["file"]).read_bytes() for p in manifest["parts"])
    ids = lambda data: re.findall(rb"(?m)^### (F[0-9]+(?:\.[0-9]+)?)\s", data)
    if ids(active) != ids(archive):
        errors.append("Feature IDs/order differ from original plan; review an intentional plan revision")
    for name in ("AGENTS.md", "context/HANDOFF.md"):
        if len((ROOT / name).read_text(encoding="utf-8")) > 6500:
            errors.append(f"{name}: exceeds 6500-character maintenance budget")
    if errors:
        raise SystemExit("\n".join(errors))
    print(f"PASS: {len(FILES)} active documents, {len(ids(active))} feature IDs, archive checksum")


if __name__ == "__main__":
    check()
