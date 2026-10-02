# Production operations recheck — 2026-10-01

Scope: production API from reviewed PR #69 commit
`1c0cd5938f551b2aecf52bb3c02fafe6fe7bb563` through PR #71 merge
`351a7db`, Upstash Redis, the temporary local worker, and private telemetry
configuration. The initial configuration check used two bounded paid assistant
probes; the later production evaluation is reported separately. No corpus
reload was made.

## Passed

- An independent reviewer approved the environment-only production API redeploy
  on the reviewed PR #69 commit after its five required CI jobs passed. Vercel
  deployment `dpl_GqrfnhbhABUPg92ZkmYH1SBSkxi3` reached READY and serves the
  production alias. `/health`, `/health/db`, and `/health/redis` returned 200.
- The production jobs admin token is configured as a sensitive, production-only
  environment variable. `/v2/admin/metrics` returned 403 without a token and
  200 with the private token. No token value was recorded here.
- The API's OTLP endpoint, protocol, and headers match the private approved
  collector settings. The local worker has the same settings. A safe local
  trace/metrics export probe flushed successfully after header normalization;
  the worker restarted without exporter errors in its second private log.
- The user selected the free Personal organization's existing workspace for
  HarmonicColorGraph. Its current service key returned 200 on a read-only
  project list after correcting the workspace ID in the private file. The
  `harmonic-color-graph-production` tracing project was created there, and a
  synthetic no-user-data trace was visible through the SDK. The UI shows the
  Developer Free plan, no card added, and zero of 5,000 monthly traces used
  before the probe. An independent reviewer approved production-only export.
  Vercel deployment `dpl_F1UzjhPx9BJ2uq9jYLx38Xs9oAqw` reached READY on
  the reviewed PR #69 commit with the key stored as sensitive. API/DB/Redis
  health and admin authentication still pass.
- Production `evaluation_run` job `68afd2aa-d72b-423b-864a-e47907737795`
  completed on attempt 1. A duplicate request with the same idempotency key
  returned the same job ID; a changed payload with that key returned 409.
  Persisted events show queued, running, progress at 0.05 and 0.95, and
  completed at 1.0.
- With the worker stopped, production job
  `23f66f99-0610-453e-a72a-f8b567b3bb88` remained queued. It completed on
  attempt 1 after the worker restarted, with persisted progress events.
- A request for a deliberately absent corpus artifact
  (`83b62940-27ba-458a-8ca6-15bfcd420361`) failed with `invalid_job` on
  attempt 1, without loading or changing the active corpus. The admin manual
  retry returned 202; the worker ran attempt 2 and failed for the same missing
  artifact. This establishes manual retry, not retryable-failure dead-letter
  behavior.
- The user reset the previously exposed Supabase password in the dashboard.
  The new password passed direct Postgres and shared transaction-pooler
  connection checks on the first attempt. The API's sensitive `DATABASE_URL`
  was updated for production and preview; the private local worker URL was
  updated. An independent reviewer approved a rotation-only redeploy on the
  PR #69 commit. Deployment `dpl_7W8V1JQ1uZWpaPJkoAdJgkW2yyxw` reached
  READY at that exact commit. Production `/health`, `/health/db`,
  `/health/redis`, and a deterministic graph neighborhood returned 200;
  admin metrics returned 403 without the token and 200 with it. The restarted
  worker reached Postgres/jobs/Redis, had no authentication or exporter errors
  in its private startup log, and completed production job
  `7ea0b5be-08e9-41ad-8b63-4a7398e99403` on attempt 1.
- A bounded production assistant query `14451d9e-65b8-40ee-be25-32d58a276356`
  returned HTTP 200 and 22 SSE events ending in `final`. Its exact durable
  audit has route `explain`, a final response, no error, 7,239 input tokens,
  960 output tokens, $0.022350 cost, and 14,004 ms latency. Cumulative new
  evaluation spend reached $4.731855 of the authorized $10. LangSmith received 43
  runs including three model runs. A scan of those records found none of the
  known database, Redis, Vercel, jobs-admin, or LangSmith credential values or
  their URL/key prefixes.
- PR #70 passed all five required CI jobs and merged at `2421018` after
  independent review. It fixes the first probe's `GeneratorExit` root trace
  by exhausting the graph iterator before sending `final`; a local regression
  failed before the change and passed after it. Vercel deployment
  `dpl_BdhbtqC31mBnvFZuYPC3JZaHhi7C`
  reached READY at that exact commit. API/DB/Redis health and authenticated
  admin metrics still pass. Production assistant query
  `f31ad024-8b51-4623-a52a-53a602935f06` returned HTTP 200 with 22 SSE
  events ending in `final`. Its exact durable audit has route `explain`, no
  error, a final response, 8,148 input tokens, 1,025 output tokens,
  $0.024786 cost, and 14,381 ms latency. The matching LangSmith root has an
  end time and outputs, no error, and 41 child runs in the inspected sample.
  Cumulative new evaluation spend is now $4.756641 of the authorized $10.
- With the normal worker cleanly stopped and no other active jobs, a scoped
  worker injected a retryable timeout into production job
  `0dd1a92a-73f6-44c9-b7e3-503dd3113cc0`. The live Postgres ledger and
  Upstash queue recorded attempts 1 and 2 as `retrying`, then attempt 3 as
  `dead_letter`. An authenticated manual retry returned 202 and queued the
  same job. The restored normal worker completed attempt 4; persisted event
  history covers each transition. No corpus artifact was changed.
- An isolated API process used the production database with a deliberately
  unreachable Redis address. Its job submission returned 503
  `queue_unavailable` with persisted queued job
  `db0deb02-12bb-44f9-b947-6770aa3a74a0`. The normal worker reconciled and
  completed that job on attempt 1 through the real Upstash queue. This tests
  outage handling without taking the shared production Redis service down.
- A local API process with both OTLP and LangSmith tracing disabled returned
  200 for application, database, Redis, and graph-neighborhood checks and
  retained request trace IDs. Production admin metrics returned 403 without
  the private token and 200 with it, exposing API latency, status, Redis hit
  rate, queue depth/retries/dead letters, AI spend and model/tool aggregates.
- PR #71's required Compose smoke passed on a Docker GitHub Actions host after
  independent review. It built and started the full API, frontend, Postgres,
  Redis, and worker stack; checked dependency and worker health; completed a
  queued job; restarted Postgres, API, and worker and confirmed the job's
  idempotency record persisted; then stopped Redis, confirmed a 503 response
  with a durable job ID, restarted Redis, and observed that job complete.
  All five required CI checks passed before merge `351a7db`.
- A local scan of 16 worker log files found no exact matches for seven current
  private credential values, including the rotated database URL and configured
  export credentials. This supplements the earlier LangSmith run scan; it does
  not prove arbitrary log content is free of all sensitive data.
- The same seven-value exact scan found no matches in 37 durable production
  assistant final responses. This is a known-secret check, not a general
  sensitive-data classifier.
- The approved Grafana Cloud stack became available after its initial
  provisioning delay. Its own portal showed about 2.2k active metric series
  and 6.88 MB of ingested traces. Tempo opened audited assistant trace
  `1fc59ef2bbc508517c78c5a8ad7fd684`: successful POST 200, 15.49 s,
  43 spans, including `http.request`, `db.query`, `ai.model`, LangGraph nodes,
  `ai.tool.recommend_next`, and nested recommendation retrieval/ranking spans.
  The trace ID matches the HTTP header and durable request log.
- Tempo also opened local-worker trace
  `a97b67f13de177d033b064f9da12865a` from the processed retry job:
  `job.process` plus six `db.query` spans, 308 ms. The trace ID matches the
  worker's structured job log. The Grafana traces list shows live
  `harmonic-color-graph-worker` `redis.queue_receive` spans. Thus both API
  and worker exports are present in the destination, though they are separate
  traces.
- Grafana Prometheus Explore listed 59 application metric names, including
  `api_request_count_total`, AI tokens/model latency/cost, Redis latency and
  cache hits/misses, queue depth, and worker busy/idle time. Running the
  `api_request_count_total` query returned 27 labeled time series. This
  confirms destination metrics beyond collector acceptance.
- An authenticated production admin snapshot on 2026-10-02 showed 391 API
  requests with p50/p95/p99 of 84.5/12,359.2/16,593.8 ms, Redis instance
  cache hit rate 0.1081, queue depth zero, seven completed jobs, two retry
  events, and no *current* dead letters after the manual retry. It reported
  86 AI queries, a 0.4074 fallback rate, and $3.176013 cumulative AI cost in
  that endpoint's accounting window. These aggregates include probes beyond
  the fixed 40-case acceptance set.

## Second database credential rotation — 2026-10-02

A diagnostic exception exposed the then-current database connection URL in an
internal tool result. The user generated a distinct replacement and submitted
the Supabase reset, then saved it only in the private operations file. The
local worker was stopped before reset. The new credential authenticated
against both Supabase IPv4 pooler modes. After independent review, Vercel's
production/preview `DATABASE_URL` was changed to the transaction pooler
(`:6543`) and the persistent local worker was changed to the session pooler
(`:5432`). No value is in this report, Git, or chat. A direct IPv6 route from
this machine was unreachable and appeared in Supabase network bans; it was
left unchanged because the poolers restored the services.

The exact reviewed API revision `351a7db` redeployed READY as
`dpl_GMcN4zsH5hogeNFUYoJjTytHFVma`; public API, database, and Redis health
each returned 200, and unauthenticated admin metrics returned 403. The worker
dependency check passed against database, jobs, and Redis, then the background
worker restarted. The temporary $3 AI daily cap allowed the three remaining
production evaluation cases, which delivered and reconciled without another
protocol interruption. The cap was restored to $2 and API revision `351a7db`
redeployed READY as `dpl_35BWeZAfgeeGoW3Wv5DoSzog565e`; API/database/Redis
health returned 200 again. Both cap changes were verified by read-only Vercel
environment metadata. A later, independently reviewed temporary $3 window
allowed one real UI demo with a $0.064958 audited cost; the cap returned to
$2 immediately afterward. PR #73's reviewed fix passed all five CI jobs and
merged as `bb82911`; API and frontend deployments are READY at that commit.
API, database, and Redis health each returned 200 after deployment, and the
production cap is confirmed at $2. Total task evaluation spend is $6.091257
of $10.

## Open or unverified

- The assistant trace has no Redis or worker span: AI rate/budget accounting
  uses Postgres, and the worker processes separate administrative jobs. A literal
  single trace ID through assistant models and a separate worker job is not
  produced by the current architecture.
- Shared Upstash itself was not stopped; the isolated API outage probe above
  tested the same failure and recovery branches against production Postgres.
  The Docker-host Redis removal check passed in PR #71's required CI.
- Docker is unavailable on this Windows host; the Compose operations were
  verified on the GitHub Actions Docker host, not repeated locally.
- Previously built immutable preview deployments may still contain the old
  password, which is invalid after rotation. They were not used for live checks.
  The temporary worker only runs while this computer is awake.

All private configuration is outside Git. No secret values or log bodies are
included in this report.
