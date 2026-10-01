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

Detailed archive, inventory, restore list, and logs are private under
`C:/Users/sidds/.hcg/rollback-cv-2026-09-a/`; they are not repository artifacts.

## Pending

- Complete `cv-2026-10-b` build and artifact validation.
- Rehearse the full new load, maximum measured storage, idempotency,
  forced-failure recovery, and old-corpus rollback after the new load.
- Review the [maintenance procedure](../runbooks/corpus-maintenance.md),
  final artifact hashes, and exact release commits before activation.
- Production maintenance/deployment/activation and post-load acceptance.

This evidence proves recoverability of the existing corpus, not acceptance
of the new corpus or authorization to skip the separate activation review.
