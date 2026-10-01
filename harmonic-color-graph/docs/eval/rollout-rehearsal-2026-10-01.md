# Corpus rollback rehearsal — 2026-10-01

Production remains on `cv-2026-09-a`; no production corpus mutation has occurred.

## Passed

- Private custom-format `hcg` archive: 33,319,619 bytes;
  SHA256 `0eaf8172e2f5cf69948c042ab3b4100a317517af1f5f2d5aa48bc663990688f7`.
- Full restore on loopback-only PostgreSQL 17.11 with pgvector 0.8.2.
  All 33 table counts and sequence values matched production inventory.
  Restored active version: `cv-2026-09-a`.
- Separate selective rollback rehearsal: committed truncation of the exact
  16-table corpus allowlist, followed by ordered single-transaction restore
  with constraints enabled. All 33 counts matched before/after; 17 other
  tables were preserved. No `CASCADE`, trigger bypass, or schema deletion.
- Local `hcg` size: 252,960,768 bytes after full restore;
  1,155,072 bytes after committed corpus reclamation. Production before
  reclamation was 279,871,488 bytes; local restore compacted existing bloat.

- Preserved the public pre-activation graph snapshot (1,935 bytes; SHA256
  `0fbf060bbbce72322834922a12417a0d4411efb92b2ea856a62461b4dc0250cf`).
  The old embedding map returned 404; rollback must preserve that absence.

Detailed archive, inventory, restore list, and logs are private under
`C:/Users/sidds/.hcg/rollback-cv-2026-09-a/`; they are not repository artifacts.

## Build recovery

The first full build completed analysis but hit the 8 GiB memory guard while
hashing the resulting whole-frame NDJSON (8,410 MiB observed). The completed
Parquet file contains all 679,807 input songs, 2,292,102 derived sections,
44,500,844 tokens, and 47,201,852 relationship labels. All input song IDs are
accounted for; no analyzed songs were lost or skipped.

Bounded hashing recovered the existing output in 14.42 seconds with a
maximum observed 2,013,724,672-byte process RSS. Sections content SHA256:
`d506394ff6ea7826639ab8b7789c2bb9005190e0b6e060213f61247f6b4f47eb`.
The analysis used `9c9a5c0a03264f58fc1a3bbd379b941c9c9b2838`; its elapsed
stage timing was not recovered. Details are `.agent-logs/analyze-recovery.json`
and the manifest's `analysis_recovery` field.

The pipeline now shares the loader's bounded hashing approach, saves metadata
after each successful stage, and marks running builds unavailable to the
loader. Compatibility tests preserve existing content hashes across batch
boundaries, nested values, nulls, Unicode, and empty artifacts. The memory
ceiling remains unchanged. Aggregate and subsequent stages still need to run.

## Pending

- Complete `cv-2026-10-b` build and artifact validation.
- Rehearse the full new load, maximum measured storage, idempotency,
  forced-failure recovery, and old-corpus rollback after the new load.
- Review the [maintenance procedure](../runbooks/corpus-maintenance.md),
  final artifact hashes, and exact release commits before activation.
- Production maintenance/deployment/activation and post-load acceptance.

This evidence proves recoverability of the existing corpus, not acceptance
of the new corpus or authorization to skip the separate activation review.
