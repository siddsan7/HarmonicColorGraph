# Production Claude evaluation — 2026-10-01/02

The 40-case production HTTP/SSE evaluation completed against active
`cv-2026-10-b` and API revision `351a7db`. The private, version-pinned ledgers
reserve each bounded request before sending it and reconcile final SSE frames
against durable Postgres audits. No prompt or response text is in this report.

All 40 distinct benchmark cases delivered final frames that exactly match
their durable audits. The API first returned a model-free hourly 429
with a retry time near 2026-10-02 03:00 UTC. At that reset it returned a
model-free daily-budget 429: UTC-day audited cost was $1.284473, and the next
conservative $0.75 reservation would exceed the production $2 daily cap.
There was no new metered cost or unknown reservation from either rejection.
The production daily cap was temporarily raised to $3 after review for the
last three cases, then restored to $2. The final three delivered and audited
normally after the database credential rotation.
The earlier interrupted `similar-06` attempt
remains HTTP-delivery unverified and its audited cost is included in total task
spend. A separate, later `similar-06` request delivered and was scored.

## Ten-query latency sample, selected before completion

The representative route-balanced sample uses the first two benchmark cases
from each of recommend, generate, explain, and similar, then `compare-01` and
`clarify-01`. This selection is fixed before `clarify-01` completes. The gate
is p50 end-to-end HTTP/SSE time under 8 seconds across those ten queries.
The first ten benchmark cases, all recommend, are also reported as a route
specific diagnostic; their observed p50 is 10,734 ms and fails the same
target. The route-balanced ten-query p50 is 7,250.5 ms and passes the
under-8-second gate. Individual request times span 812–19,125 ms.

At the earlier 37-case checkpoint, 18 one-Sonnet-call requests had median
6,515 ms and 19 two-Sonnet-call requests had median 10,469 ms. This describes
correlation, not a proven causal performance diagnosis. Across the completed
40-case run, 12 responses carried labeled fallbacks.

## Twenty-query live routing set

The live routing subset uses `recommend-01` through `recommend-08`,
`generate-01` through `generate-04`, `explain-01` through `explain-04`,
`similar-01` and `similar-02`, `compare-01`, and `clarify-01`. This fixed
selection spans all six routes. All 20 were correctly routed, schema valid,
and delivered through a final SSE frame.

## Acceptance status

The final 40-case score meets every specified quality threshold:

| Metric | Production | Required |
|---|---:|---:|
| Schema validity | 100% | 100% |
| Must-not patterns | 100% | 100% |
| Routing | 100% | >=90% |
| Intent match | 75% | >=75% |
| Tool correctness | 100% | 100% |
| Theory validity | 100% | 100% |
| Required theory tags | 100% | 100% |
| Fact coverage | 100% | >=95% |

There are 72 claim assessments and 12 intent-scored cases. The 40-case run's
accounted cost is $1.269658, including the earlier delivery-unverified
attempt. All task AI evaluation spending is $6.026299 of the authorized $10.
The private ledger preserves request identifiers and exact audit matches.
This passes the specified production quality thresholds and the predeclared
route-balanced latency sample; the recommend-only latency diagnostic fails
its 8-second target.

Read-only production audit inspection found candidates in 23 of the delivered
cases and cited claims in 29. `generate-05` returned three candidate
progressions for a request to make the result playable; its parsed `export`
flag was false and no server-side playback payload was produced. The frontend
builds playable sequences from candidate chords through deterministic
analysis. A separate real production Chromium demo of a three-chord D-minor
generation request returned HTTP 200 with three options, three candidate
citation sections, an enabled Play control, and visible Stop playback after
clicking. The matching durable audit `3ab8e21e-973e-4060-9f99-f8669344d4aa`
records route `generate`, three candidates with cited facts, no error, and
$0.064958 cost. Its server-side playback field was null, confirming the
optional export-intent miss; the reviewed fix is in the next PR. This verifies
browser playback control behavior, not audio quality. No song or audio
listening judgment is made here. Total task AI spending after this demo is
$6.091257 of $10.

The weekly workflow is configured for 06:17 UTC Mondays in
`.github/workflows/ai-eval.yml`. Its latest manual run, GitHub Actions
`36840188769` on `bd42171`, succeeded and published a seeded-fixture report.
No scheduled run has occurred yet. That workflow's fixture result is not the
production-corpus acceptance result above.

The deployed `/assistant` page passed the existing axe accessibility scan in
desktop Chromium and a 412-pixel mobile Chromium context, on both initial and
rendered-result views (one test at each viewport). The result view used mocked
SSE so this accessibility check did not spend model tokens; a real production
UI demo used the production response above; a post-release regression check
of the server-side playback field remains pending.

The live evaluation reached the production hourly limit and received 429 with
`Retry-After`, with no new model charge for that rejected request. The focused
`test_ai_query_v2.py` suite passed 24/24 locally, including the 21st-request
limit, daily budget rejection and durable rejection audit, metered-cost cap,
and conservative reservations after model/workflow failures. These are local
budget-path tests; the live hourly 429 is separately observed. A read-only
four-hour production audit query showed 40 successful rows and two
`ip_rate_limit` rows; successful rows include earlier probes and the one
delivery-unverified attempt, so this count is not the benchmark completion
count.

Grounding-validator and 30-case adversarial-corpus integrity tests passed
55/55 locally. The production benchmark's case-specific must-not patterns
passed 40/40; the local adversarial tests and 40-case production
benchmark exercise different prompt sets. The 30-case adversarial corpus was
not itself sent to the production model.
