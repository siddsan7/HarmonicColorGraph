# Paired live HTTP evaluation — 2026-10-20

Six paired recommendation cases show faster completion and candidate delivery,
with lower observed cost. Intent match is unchanged and explanation fallback
worsened. This is a small controlled-runner diagnostic, not production acceptance.

## Protocol and identity

[Run 39417065727](https://github.com/siddsan7/HarmonicColorGraph/actions/runs/39417065727)
used two isolated loopback HTTP/SSE servers in one GitHub Actions runner:
baseline `8ed6dfb5e63a7c5e417e3ffedd17d532e4548dec` and candidate
`e668de33d217417f4ef7dff53c576aa46b8f44b8`. Harness revision:
`1e9bae2402ffda5ce28e54a2ae827fec109034a8`.

The first ten unchanged benchmark recommendation cases were selected before
requests. Cases 01–06 completed, in alternating AB/BA order (three each).
The next pair was refused because its $1.50 reservation would exceed the
remaining daily allowance. No outcome-based case selection, paid warmup,
transport retry, benchmark/rubric change or scorer tuning occurred.

Both arms used live `claude-haiku-4-5-20251001` and `claude-sonnet-5`, resolved
through the model-free catalog before inference. Both used the same live corpus
`cv-2026-10-b`. Active version, load timestamp and manifest hash matched before,
after and during independent review. This checks corpus identity, not every
database row. Retrieval was live, not a seeded fixture.

## Comparable paired results

Each arm has six completed requests. First candidate means its validated SSE
event, or the final event with candidates when there is no preview. It does not
measure browser paint. Rates below use the same six cases in each arm.

| Metric | Baseline | Candidate | Observed change |
|---|---:|---:|---:|
| Completion median | 16.506 s | 11.728 s | 28.9% lower |
| First-candidate median | 16.506 s | 2.734 s | 83.4% lower |
| Combined intent / color-axis match | 5/6 (83.3%) | 5/6 (83.3%) | unchanged |
| Intent parse match | 6/6 | 6/6 | unchanged |
| Explanation fallback | 0/6 | 1/6 | regression |
| Requests requiring repair | 5/6 | 3/6 | 83.3% to 50% |
| Model calls, total / per request | 17 / 2.83 | 15 / 2.50 | 11.8% fewer |
| Input tokens, total | 99,752 | 82,857 | 16.9% fewer |
| Output tokens, total | 7,014 | 4,925 | 29.8% fewer |
| Observed cost per completion | $0.042990 | $0.033877 | 21.2% lower |
| Total paired cost | $0.257939 | $0.203259 | $0.054680 lower |
| Routing, tools, schema, must-not, theory, required tags | 6/6 each | 6/6 each | unchanged |
| Fact coverage proxy | 100% | 100% | unchanged |

Candidate completion was faster on four of six cases. It still exceeds the
8-second completion target. The candidate's fallback was case `recommend-04`:
the explanation failed the `song_provenance` validator. The strict validator
remained enabled and the deterministic fallback was retained. Independent
regrading of every stored response matched the recorded scores.

The arms produced different explanations: eight baseline claims versus fourteen
candidate claims. Lower observed cost is not proof of equal-content or equal-
quality savings. The fact coverage proxy checks deterministic validation; it
does not establish semantic entailment or musical usefulness. This sample cannot
certify p95, broad candidate coverage, held-out ranking quality, or production
Vercel performance. No production target is declared reached.

## All-attempt accounting and cleanup

The initial [run 39416590948](https://github.com/siddsan7/HarmonicColorGraph/actions/runs/39416590948)
completed one baseline request, then the harness stopped on a fully metered
validation failure followed by repair. The original artifact and reservation
ledger are preserved. Independent review verified all three calls and released
only the unused reservation. The corrected harness checks each callable's usage
delta and matches all usage calls to the durable audit. Unknown usage still stops
the run. This pilot is excluded from paired timing and quality estimates.

| Spend | USD |
|---|---:|
| Reconciled project spend before this work | 10.157483 |
| Unpaired initial attempt | 0.050117 |
| Six pairs | 0.461198 |
| **New spend, all thirteen requests** | **0.511315** |
| **Cumulative project spend** | **10.668798** |
| Approved cumulative ceiling | 12.157483 |
| **Remaining allowance** | **1.488685** |

All thirteen audits reconcile to model usage: 35 calls, 202,280 input tokens,
13,210 output tokens, zero unknown usage and zero pending audits. Counts include
failed validation calls and repairs. These are application usage records, not a
provider invoice reconciliation.

The temporary database role was set NOLOGIN and the GitHub secret was deleted.
Managed PostgreSQL denied `DROP OWNED`; exact grant revocations resolved cleanup
without granting role membership. Independent checks confirmed zero temporary
roles, zero temporary policies and no evaluation database secret. The weekly
paid workflow is `disabled_manually`; the ordinary benchmark job was skipped in
both evaluation runs. No production deployment, merge or corpus activation occurred.

## Verification and evidence

Seventeen final model-free evaluator/access tests pass, including the managed
Postgres cleanup regression. Ruff lint/format, documentation integrity and diff
checks pass. All five CI jobs and both previews passed at `1e9bae2`; final report
and cleanup checks are recorded in PR78. Independent review verified costs,
all paired UUIDs/order/usage, every grading field, corpus identity and cleanup.

[Machine-readable evidence](paired-live-2026-10-20.json) includes individual
case measurements, audit IDs, artifact hashes, corpus/model identities and the
pilot reconciliation. No credentials or provider response text are published.
The earlier [preflight report](paired-live-preflight-2026-10-20.md) records the
budget blocker before the user authorized an additional $2.

The next quality investigation is the provenance repair failure. Keep the closed
ranking holdouts and unchanged benchmark intact. Any further live run requires
fresh spend reconciliation and enough allowance to reserve its full request pair.
