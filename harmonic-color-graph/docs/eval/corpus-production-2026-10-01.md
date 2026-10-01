# Corrected corpus production activation

`cv-2026-10-b` was activated on 2026-10-01 after independent review, a fresh
production backup, full and selective restoration, and a fresh capacity
rehearsal. This replaces `cv-2026-09-a`. Human listening is not covered.

## Provenance and recovery

The frozen manifest SHA256 is
`35d999636616d6f5c45db8ff56c137b6720b48524042f771f633231366230605`.
The [release report](corpus-release-cv-2026-10-b.md) identifies the verified
source, generated reports, and browser asset hashes.

The final private archive SHA256 is
`251175bcaef58bb54b5e0db1906aae755a433584e1cb566bcdd7228e5506c064`.
An exported PostgreSQL snapshot aligned the dump with the table inventory.
All 33 table counts and content hashes matched the full local restore.
Selective recovery then restored the 16 corpus tables and two corpus
sequences while preserving the other 17 tables and all local sequence values.
The old browser graph was archived; the old embedding map returned 404.

Two earlier verification failures were retained. Windows and production
sessions serialized timestamps, sorted text, and formatted floats differently.
The final verifier fixes UTC, ISO DateStyle, `COLLATE "C"`, and
`extra_float_digits=3`. Exact comparisons pass without numeric tolerances or
changes to stored data. Non-corpus sequence observations are not claimed to
be snapshot-isolated and are never selectively restored in production.

## Maintenance replacement and capacity

Reviewed runtime `6928ea8956a2877d6840eb7ef03036d41853bedd` was deployed in
maintenance mode. The idle temporary worker stopped, and no queued/running/
retrying jobs remained. Older immutable deployment URLs were not claimed to
be drained: they could fail or block during the documented outage. Fresh
writer/dependency checks and bounded lock waits guarded reclamation.

Migration 0013 compacted the incoming-edge index without changing rows or
outgoing uniqueness. The replacement used the allowlisted maintenance
procedure, frozen artifacts, and loader index compaction. The reviewed driver
SHA256 was `994eb8e05ba06d062ed6f4b44192c88d1cf814e8c5846f4748ae4a8c5ef6a8a5`.
Its process lock spans committed gaps, and errors trigger selective recovery.
Monitoring failures and recovery failures remain explicit in its report.

| Measurement | Fresh local rehearsal | Production replacement |
| --- | ---: | ---: |
| Final `hcg` bytes | 313,786,368 | 313,180,160 |
| Final database bytes | 323,180,211 | 325,340,307 |
| Sampled physical database peak | 381,572,787 | 384,552,083 |
| Final schema headroom | 786,432 | 1,392,640 |

Both unchanged gates passed: 300 MiB for `hcg`, 400 MiB for the database.
The loader checked storage before activation; the physical database was
sampled every second through commit and final verification. These are sampled
peaks, not guarantees of an instantaneous maximum. No monitor errors occurred.
The subsequent load was an idempotent no-op. Headroom remains narrow, and
later telemetry growth must be measured independently.

## Production correctness

Read-only acceptance confirmed the loaded manifest exactly matches the frozen
release, all 15 norms match, and stored profiles cover exactly 301 functions,
22,869 global transitions, and 8,831 patterns. The chord2vec default retains
34/40 intrinsic triplet results. Function and pattern queries use their HNSW
indexes. Related loops and actual canonical rotations are returned correctly.
Recommendation retrieval supplies 12 graph and 12 embedding candidates, with
embedding provenance in the ranked response.

Direct workstation-to-database warm p95 was 19.68 ms for function neighbors
and 96.60 ms for structural similarity. These measurements are not public
HTTP latency. The initial exact norm comparison encountered the same rounded
float-output setting; the retained failure was corrected by lossless session
serialization, and the unchanged exact comparison passed.

PR62 merged at `3dcafb9cda6940b7eeab8bf133d1cc7ffc85cf3c` after independent
artifact review, all five CI jobs in run 36825465653, and production database
acceptance. Both public browser asset hashes matched the frozen release.
Maintenance is off on deployment `dpl_5NiCU3yi5tzhsCaw8dVky8tFHpur`, with
API, database, and Redis health returning 200. The temporary worker restarted
healthy and idle. Public UI and AI acceptance remain pending.

## Public HTTP latency regression

The production verifier confirmed response correctness and matched all 40
measured requests to durable audit rows. Back-to-back warm server p95 failed
the unchanged 120 ms gate: function 2,068 ms and pattern 1,652 ms. Client
latency is recorded separately. A verifier route typo was corrected and its
failure report retained; it did not alter the measured samples.

Spaced requests returned server times of 39–41 ms. Runtime logs showed fast
Redis and SQL calls. The synchronous telemetry flush blocked the async event
loop while exporting over the network. A regression test failed before the
fix and passed after moving the flush to the worker thread pool. The flush
remains awaited so serverless execution retains its export lifetime.

All 12 telemetry tests and the full backend lint, format, and unit checks
passed locally. The runtime diff received independent review. Release CI and
post-deployment back-to-back latency verification remain required; this is
not yet a production performance pass. Sustained worker-pool contention is
still possible and must not be inferred away from the focused test.

Private evidence is retained under `~/.hcg/rollback-production-20261001T064908Z`:
backup review, local restore verification, fresh capacity rehearsal, procedure
hashes, and production activation report. The repository-local read-only
acceptance report is `.agent-logs/corpus-production-acceptance.json`.


### First telemetry release and remaining contention

PR63 passed all five CI jobs in run 36829958374 and independent exact-head
review, then merged as `630ebf5094e12c58d9df91c1b506d16e6ee52514`.
Deployment `dpl_CQ8Zm6jkNrRLAWfoAAobD4r7nNED` reports healthy and the reviewed
production label `cv-2026-10-b`. The rollback notes require restoring the
previous corpus label alongside any corpus rollback.

Fresh back-to-back measurements preserve response and audit correctness.
Function server p95 is 51.55 ms (passes), but pattern p95 is 510.04 ms
(fails; median 85.63 ms). The original report is retained as
`corpus-production-http-before-telemetry-fix.json`. This is an improvement,
not a complete performance pass.

A second regression reproduced shared worker-pool starvation during blocking
export. The follow-up coordinator uses one export task per event loop,
coalesces waiting requests, and records which completed requests each export
covers. Requests arriving during an export await a subsequent one. Export
uses the asyncio executor rather than AnyIO's endpoint worker capacity.
Cancellation of one request does not cancel the shared export. Focused tests
cover capacity, overlapping arrivals, cancellation, exceptions, and loop
isolation. Production verification remains required after release.

Public browser checks on the corrected corpus also verified structural and
surface rotation matches, exact map lookup, Workbench URL restoration,
analysis/color/song evidence, smooth-intent recommendations, active playback,
and generation of three paths plus distinct A/B/C continuations. The 390 px
Workbench layout has no page-wide overflow. These observations do not replace
human listening, Safari/iOS, or the complete production UI acceptance set.


### Coalesced export release: representative HTTP gate passes

PR64 passed all five CI jobs in run 36831886915 and independent exact-head
review, then merged as `247b0256f2d427dc7398b28602bda8511914e02c`.
Production deployment `dpl_EMASMehhnrHTknYWbjyiA3Pmfcd3` serves that version
with status `ok` and corpus label `cv-2026-10-b`.

The unchanged verifier passed all correctness checks and 40 durable request
log matches. Each query used two warmups and 20 measured back-to-back calls:

| Query | Server p50 | Server p95 | Client p50 | Client p95 |
| --- | ---: | ---: | ---: | ---: |
| Function neighbors | 40.43 ms | 42.11 ms | 53.31 ms | 148.37 ms |
| Structural patterns | 72.19 ms | 76.88 ms | 87.59 ms | 113.41 ms |

Both server p95 values pass the unchanged 120 ms gate. These are two warm
representative queries, not endpoint-wide or cold-start guarantees. Historical
failures remain in `corpus-production-http-before-telemetry-fix.json` and
`corpus-production-http-after-threadpool-fix.json`; the passing report is
`corpus-production-http.json`. The live AI benchmark starts only after this
pass and uses a separate durable spending ledger.
