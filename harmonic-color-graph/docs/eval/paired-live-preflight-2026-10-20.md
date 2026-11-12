# Paired live evaluation preflight — 2026-10-20

Historical preflight: the user subsequently approved $2 additional and pausing
the weekly workflow. See the [completed paired evaluation](paired-live-2026-10-20.md)
for current results, final spend and verified cleanup.

Status: blocked before credential provisioning or model calls. The user approved
up to $2 **within the remaining $10 project allowance**. Reconciliation found
identified spend of $10.157483, leaving no allowance. New spend in this work: $0.
No before-and-after live metrics were obtained.

## Spend reconciliation

| Evidence | USD |
|---|---:|
| Historical acceptance ledger, including its seven attempts | 6.026299 |
| October 2 production UI audit `3ab8e21e-973e-4060-9f99-f8669344d4aa` | 0.064958 |
| Subsequent October 18 database audit | 0.001509 |
| [October 5 scheduled live fixture evaluation](https://github.com/siddsan7/HarmonicColorGraph/actions/runs/37326217686) | 1.378142 |
| [October 12 scheduled live fixture evaluation](https://github.com/siddsan7/HarmonicColorGraph/actions/runs/38269994351) | 1.309303 |
| [October 19 scheduled live fixture evaluation](https://github.com/siddsan7/HarmonicColorGraph/actions/runs/39258407648) | 1.377272 |
| **Identified total** | **10.157483** |
| **Amount above the $10 allowance** | **0.157483** |

The three scheduled runs were absent from the prior project subtotal of
$6.092766. Each artifact reports 40/40 completed live fixture cases, no
unknown-cost cases, and matching per-model and total costs. An independent
reviewer checked the artifacts and arithmetic. These are application usage
records, not a provider invoice reconciliation.

Private historical ledger SHA256:
`bb18e25428820d724a2e7298194a9af77037c44c22f562bce10c35581f5cdf4c`.
Compact artifact hashes and aggregate evidence are in
[the reconciliation record](paired-live-preflight-2026-10-20.json).
Raw artifacts remain in ignored local evidence storage. No credentials or
customer prompts are included in this report.

## Endpoint identity

| Target | Verified application commit | Health and configuration |
|---|---|---|
| Baseline preview `harmonic-color-graph-jjueus2br-siddsan7s-projects.vercel.app` | `8ed6dfb5e63a7c5e417e3ffedd17d532e4548dec` | HTTP 200; database 200; Redis 503; corpus reported `unversioned`; no model key configured |
| Candidate preview `harmonic-color-graph-3klkozqom-siddsan7s-projects.vercel.app` | `e668de33d217417f4ef7dff53c576aa46b8f44b8` | HTTP 200; database 200; Redis 503; corpus reported `unversioned`; no model key configured |
| Production `harmonic-color-graph-api.vercel.app` | `1db9cbf6a2cc57c34e76ec2f9ff862a5b7e3aa38` | HTTP 200; corpus `cv-2026-10-b` |

The previews are the intended application revisions but cannot serve the paid
comparison as configured. A controlled Actions runner with both revisions,
the existing repository model secret, and a temporary restricted database role
was prepared as an alternative. It was **not provisioned or dispatched**.
Its latency would describe that runner, not production Vercel latency.

## Available metrics and limits

These historical scheduled results use seeded retrieval fixtures and real models.
They are neither paired measurements nor measurements of the candidate revision.

| Metric | October 5 | October 12 | October 19 |
|---|---:|---:|---:|
| Routing / tool correctness | 100% / 100% | 100% / 100% | 100% / 100% |
| Combined intent match | 83.33% | 83.33% | 75% |
| Intent parse match | 100% | 100% | 91.67% |
| Color axis match | 83.33% | 83.33% | 75% |
| Schema / theory / required tags / fact coverage proxy | 100% each | 100% each | 100% each |

The candidate's unchanged offline benchmark remains routing/tool 40/40, intent
9/12 and parse 12/12, at zero model cost. Prior local feature timing improved
from 1329.26 to 670.97 ms; this is a CPU measurement, not live completion latency.
Live completion/first-result/tail latency, fallback and repair rates, calls,
tokens, cost savings, and musical usefulness remain unverified for the candidate.

## Disposition

- Passed: spend and endpoint reconciliation; independent spend review; no new
  paid calls, temporary roles, repository secrets, or deployments.
- Blocked: paired live comparison because the project allowance is exhausted.
- Skipped: paid dispatch, credential provisioning, merge and production release.
- Prepared only: local HTTP/SSE harness with durable pair reservations. Proposed
  workflow and credential helpers were moved to ignored local preparation storage;
  the tracked Actions workflow was restored unchanged.
- Pending decision: the existing weekly paid evaluation schedule remains active.
  Pause it before another scheduled charge. No new paid run is authorized by the
  exhausted allowance. Any future comparison needs a new explicit total ceiling,
  another spend check, and final protocol/credential review.

Checks: five model-free evaluator safety tests, evaluator Ruff lint/format,
documentation integrity and `git diff --check` passed. The app-local `.venv`
lacked pytest/Ruff; the same checks passed with the project's installed Python
development tools. No new live, release or deployment gates were run. The
evaluator preparation is local; the PR remote remains at `e668de3`.
