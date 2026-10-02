# Production operations recheck — 2026-10-01

Scope: production API at merge commit `1c0cd5938f551b2aecf52bb3c02fafe6fe7bb563`,
Upstash Redis, the temporary local worker, and private telemetry configuration.
One bounded paid assistant probe was made; no corpus reload was made.

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
  evaluation spend is $4.731855 of the authorized $10. LangSmith received 43
  runs including three model runs. A scan of those records found none of the
  known database, Redis, Vercel, jobs-admin, or LangSmith credential values or
  their URL/key prefixes.

## Open or unverified

- Actual Grafana ingestion and an end-to-end cross-service trace are unverified
  in the destination UI. The local exporter probe establishes collector
  acceptance only.
- The production LangSmith root run was marked `GeneratorExit` when the client
  stopped reading at the valid final SSE frame, though its child model/tool
  runs and the durable audit completed. A focused regression reproduced this
  lifecycle defect. The stream now exhausts the LangGraph iterator before
  yielding `final`; the focused test and a local trace against the approved
  project show a completed root without an error. Production verification of
  this fix awaits review, required CI, merge, and deployment. The initial
  LangSmith 403 was caused by an incorrect workspace ID.
- Bounded retry, dead-letter, and Redis-outage behavior remain production
  acceptance gaps. The Postgres integration test covers retry/dead-letter,
  manual retry, and expired-lease recovery with a memory queue; it does not
  establish those failures on the live path.
- Docker is unavailable on this host, so clean Compose startup, persistence,
  and Redis-removal operations remain unverified here. The reviewed CI Compose
  smoke job passed for PR #69.
- Previously built immutable preview deployments may still contain the old
  password, which is invalid after rotation. They were not used for live checks.
  The temporary worker only runs while this computer is awake.

All private configuration is outside Git. No secret values or log bodies are
included in this report.
