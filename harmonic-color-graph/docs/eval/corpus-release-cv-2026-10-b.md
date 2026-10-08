# Corrected corpus release

Status: activated in production on 2026-10-01 after independent review and
verified recovery. See the [production report](corpus-production-2026-10-01.md)
for acceptance results and remaining live gates.

The release uses the entire previously verified Chordonomicon CSV: 679,807
songs, 2,292,102 derived sections, and 44,500,844 tokens. No songs were skipped.
Source SHA256:
`9d2f4ccdc876a4e816712f128e4772b2af558c2a2923cce5be3a0364fbad9a8d`.
The immutable private `cv-2026-10-b` release has manifest SHA256
`35d999636616d6f5c45db8ff56c137b6720b48524042f771f633231366230605`;
all 16 output hashes and loader artifact validation passed.

## Browser assets

| File | Bytes | SHA256 |
| --- | ---: | --- |
| `public/snapshot/graph-core.json` | 395,353 | `342fca355ab6a13ab62e5e099a773f460851a6b37238bf1b9a07b35191b41f6f` |
| `public/snapshot/embedding-map.json` | 377,268 | `2716d7ab890a28cc30a157c993ddd15ab84a940ba1d41795a605dda4721e2582` |

The graph contains 120 nodes and 1,200 edges. The map contains 5,000 points
from the default chord2vec model. The graph is byte-identical to the frozen
snapshot; the map was regenerated from the frozen projection and matches the
checked-in asset byte for byte. A private validation manifest binds both
hashes to the corpus manifest above. These asset formats do not embed a
corpus-version field; release agreement is checked using these hashes.

## Evidence and release conditions

- [Corpus analysis](corpus-cv-2026-10-b.md) reports coverage and detected keys.
- [Embedding evaluation](embeddings-cv-2026-10-b.md) records chord2vec 34/40
  (85%) and FastRP 27/40 (67.5%). These are automated intrinsic checks.
- [Local acceptance](corpus-local-acceptance-2026-10-01.md) covers all stored
  colors, vector queries, recommendations, and actual desktop/mobile flows.
- [Storage and rollback rehearsal](corpus-storage-2026-10-01.md) records a
  successful complete load under the unchanged 300 MiB schema / 400 MiB
  database gates, and exact old-corpus recovery after forced failure.
- [Maintenance procedure](../runbooks/corpus-maintenance.md) governs the
  production replacement. PR60's migration 0013 and PR61's loader statistics
  refresh are required. Local schema headroom is narrow (about 0.72 MiB);
  production storage must pass independently before activation.

Before merging these assets, require the exact fresh backup, restore proof,
production code, migration, frozen artifacts, and recovery procedure to be
approved by the assigned reviewer. During maintenance, verify the new active
database version and corpus-backed queries before publishing these assets.
After deployment, compare both public asset hashes and repeat HTTP/UI checks.
Retain the old archive and asset revision for rollback.

Human music/listening review, Safari/iOS checks, live AI evaluation, HTTP job
recovery, and external monitoring are separate gates. This report does not
claim they have passed.
