# Corpus replacement within the free storage budget

Use only after an independent reviewer approves the exact artifacts, backup,
rehearsal evidence, and deployment commits. This is a maintenance replacement:
there is an intentional outage between committed space reclamation and the
new loader transaction. It is not a zero-downtime version switch.

## Preconditions

- Full build complete; manifest hashes and color/embedding checks pass.
- Rehearse the new load, idempotency, forced failure recovery, and rollback on
  a private local restore with the production PostgreSQL major version and
  pgvector version. Measure both the 300 MiB `hcg` and 400 MiB database gates.
- Keep a private custom-format `pg_dump --schema=hcg --no-owner --no-acl`
  archive, SHA256, table counts, sequences, schema inventory, and the old
  browser assets. Do not commit the archive or connection information.
- Verify an actual full restore, then verify selective corpus restore into
  existing tables. A successful dump command alone is insufficient.
- Deploy reviewed code with `HCG_MAINTENANCE_MODE=true`. Verify `/health`
  reports maintenance and corpus/job/Assistant requests return 503 with
  `Retry-After`. Stop the temporary worker after it becomes idle. Wait for
  existing API requests to drain before taking the final backup. Account for
  old immutable/preview deployment URLs and standalone MCP processes: the
  flag applies only to the deployment/process configured with it. Verify no
  corpus-writing database session remains active before reclamation.

## Exact replacement scope

The allowlist is: `corpus_versions`, `contexts`, `song_refs`,
`relationship_types`, `nodes`, `patterns`, `color_norms`, `color_profiles`,
`embeddings`, `facts`, `ngram_discount_stats`, `ngram_histories`,
`pattern_examples`, `transition_examples`, `edges`, `edges_compact`.

Preserve every other table, including jobs, job events, idempotency keys,
rate limits, AI/API logs, and legacy v1 data. Inspect foreign keys before each
run. Stop if a new dependency falls outside the reviewed allowlist; never
add `CASCADE` or delete the whole schema.

With the final private backup verified, execute one explicit `TRUNCATE` of
all allowlisted `hcg` tables with `RESTART IDENTITY`, and commit. Measure the
reclaimed size before loading. Ordinary `DELETE` does not prove space has
been reclaimed. Use the existing `pipeline.cli load` command for the exact
reviewed artifact directory. It validates artifacts and size and activates
only after the entire new load passes in its transaction.

## Recovery

If loading or acceptance fails, keep maintenance enabled and the worker
stopped. Truncate the same allowlist again to reclaim any failed-load bloat.
Restore data from the verified custom archive using `pg_restore --data-only
--single-transaction --no-owner --no-acl --exit-on-error --use-list ...`.

The restore list contains only allowlisted `TABLE DATA` entries, in the order
listed above (parents precede foreign-key children), followed by the
`corpus_versions_version_key_seq` and `nodes_node_key_seq` `SEQUENCE SET`
entries. Do not disable triggers or constraints. Preserve all other sequence
values. Compare restored counts, sequence values, active version, and key
queries with the backup inventory. Restore the old browser assets/deployment.

## Return to service

Verify active version, graph/prediction/example/color/similarity queries,
vector indexes, storage, and browser artifact version agreement. Deploy with
maintenance disabled, restart the reviewed temporary worker, then verify the
public API, job authentication/idempotency, UI flows, and telemetry. Retain
the private archive and old browser assets until post-activation acceptance
passes. Human music/listening review remains separate.
