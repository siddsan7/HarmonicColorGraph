# Temporary local worker

Use this while persistent hosting is unavailable. It consumes the same durable
job ledger and Redis queue as the configured API. It stops when the computer
sleeps, shuts down, or the process exits; this does not satisfy the persistent
hosting acceptance gate.

Store configuration outside the repository, for example in
`C:\Users\<you>\.hcg\worker.env`, restricted to your user account:

```dotenv
DATABASE_URL='postgresql+psycopg://...'
REDIS_URL='rediss://...'
HCG_ENV='development'
```

Use the database and native TLS Redis credentials for the intended environment.
Never paste them into chat or commit them. The worker does not need an Anthropic
key or the API's jobs-admin token to consume jobs. Submitting through the API
requires its existing `HCG_JOBS_ADMIN_TOKEN`. Optional OTLP credentials may be
added to this private file when worker trace export is needed.

From the app directory, verify dependencies without consuming jobs:

```powershell
python scripts/local_worker.py --env-file "$env:USERPROFILE/.hcg/worker.env" --check
```

The check prints connection status and job counts, never configuration values.
Review pending jobs before starting: this worker executes queued jobs from the
shared ledger. Graph rebuilds need reviewed corpus artifacts at
`HCG_ARTIFACT_ROOT`; the default evaluation source is the small sample fixture.
A successful sample job does not establish full-corpus quality or activation.

An `embedding_rebuild` job requires `sections.parquet`,
`transitions.parquet`, and `patterns.parquet` beneath
`HCG_ARTIFACT_ROOT/<corpus_version>/`. It runs the existing embedding,
evaluation, and projection stages. Its result identifies a complete immutable
bundle under `embedding-rebuilds/`, including source/output hashes and
`activation_required: true`. Completion means artifacts are prepared; it does
not change the active database corpus or deployed map. Review the evaluation
and integrate the bundle into a reviewed corpus build before loading it.
Failed builds do not replace prior outputs. Temporary copies of the three
inputs require corresponding free disk space.

Start one worker:

```powershell
python scripts/local_worker.py --env-file "$env:USERPROFILE/.hcg/worker.env" --stop-file "$env:USERPROFILE/.hcg/worker.stop"
```

To stop from another terminal:

```powershell
New-Item -ItemType File -Path "$env:USERPROFILE/.hcg/worker.stop" -Force
```

It finishes the current job and exits after the blocking queue wait (up to
15 seconds when idle). Before a deliberate restart, remove that stop file.
The launcher reserves loopback port 18769 to prevent a second launcher on the
same computer. It does not automatically restart after reboot. When launching
through `Start-Process`, use `-WindowStyle Hidden` and redirect logs to private
local files; retain the process ID for status checks.

The worker uses a 15-second blocking receive with a 20-second socket timeout;
API enqueue calls retain the 3-second socket timeout. Run only one worker while
using the free Redis command allowance. See PR #51 for the polling changes.
