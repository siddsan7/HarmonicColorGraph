# Corrected corpus storage rehearsal

The frozen `cv-2026-10-b` corpus initially exceeded the existing 300 MiB
`hcg` gate at 336.9 MiB. The load rolled back; the previous local corpus was
restored with all 33 table counts, content digests, sequences, and active
version matching the backup. Production was not changed.

Migration 0013 narrows the nonunique incoming-edge index. Globally unique node
keys retain destination lookup identity; queries retain version predicates.
The outgoing unique index is unchanged. Explicit maintenance loading rebuilds
edge and ngram indexes after bulk insertion, with no corpus rows removed or
values rounded. Existing versions reject this maintenance option. Ordinary
online loading retains its previous behavior.

Chord candidate selection now orders both limited selections deterministically
and retains the query chord within the candidate cap, so its usage remains
available for similarity scoring.

## Measured full local load

- PostgreSQL 17.11, pgvector 0.8.2; private restored database on loopback.
- Frozen manifest SHA256:
  `35d999636616d6f5c45db8ff56c137b6720b48524042f771f633231366230605`.
- Loaded 784,638 compact edges, 147,156 ngram histories, 32,001 color profiles,
  9,430 embeddings, and 8,831 patterns. Artifact-derived count checks passed.
- Final `hcg`: 313,819,136 bytes / **299.281 MiB**.
- Maximum sampled physical database: 381,736,627 bytes / **364.052 MiB**.
- Post-commit database: 323,245,747 bytes / **308.271 MiB**.
- 103 physical-size samples through commit, no monitor errors; idempotent
  reload returned `no-op`. Preserved-table digests and sequences matched.

The monitor samples physical database size once per second; this is not a
guaranteed instantaneous peak. It includes retained old index files. Catalog
`hcg` totals are measured before/after because reindex locks block concurrent
relation-size reads. The loader enforces both original gates before activation.
Only 0.719 MiB of `hcg` headroom remains; exact production sizing is required.

## Verification and remaining gates

- Nine focused real-Postgres checks passed: ordinary loader behavior,
  maintenance rejection on existing versions, injected size-gate rollback,
  index validity/uniqueness, recommendation isolation, and deterministic
  incoming/chord candidate results across query plans. The later seed-retention
  regression also passed on real Postgres.
- Backend non-Postgres suite passed in 128.234 seconds. Lint passed; one
  formatting failure was corrected and the complete format check then passed.
- Full-corpus incoming lookup returned all 57,904 edges for `function:M:I`
  at median 686.8 ms; chord similarity returned ten results at median 67.8 ms
  (ten warm samples each). These are local measurements, not production SLOs.
- Complete color coverage and indexed function-neighbor reads passed the next
  corpus acceptance checks; function-neighbor p95 was 1.62 ms. That acceptance
  run then failed because canonical progression rotations were omitted from
  similarity results. This separate defect must be corrected before activation.
- Full-corpus forced failure and old-corpus restoration are being rehearsed;
  production activation, deployed corpus acceptance, and human listening remain
  pending. No new paid AI calls were made.

Detailed local logs: `.agent-logs/corpus-local-load-compacted.log`,
`.agent-logs/incoming-index-acceptance.json`, and
`.agent-logs/corpus-local-acceptance-rotation-failure.json`. Private backup and
restore reports remain outside Git.
