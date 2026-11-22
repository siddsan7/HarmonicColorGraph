# Model calls and token efficiency: local measurement repair

## Goal and acceptance

Measure attempted model calls separately from returned usage records. Preserve
grounding, output schemas, call limits, usage accounting and the original
benchmark. Do not claim live savings from local fixture runs. No paid calls,
model substitutions, rate changes or new dependencies are part of this slice.

## Classic methods and fit

| Method | Fit in this implementation | Decision |
|---|---|---|
| Compact JSON and remove duplicate evidence | Compact JSON, candidate-profile deduplication, repeated perceptual prose removal and analysis reuse already exist. Workflow regression tests retain original public evidence and numeric/provenance fields. | Keep these changes. Further blind trimming can remove grounding. Prompt bytes are not model tokens. |
| Cache prompts or model responses | User query, context, corpus and candidate evidence vary. A response cache needs a complete identity, expiry and authorization design. Provider caching savings require measured usage and contract rates. | Defer until live evidence identifies repeated safe inputs. |
| Use a smaller model or deterministic bypass | Intent already has a separate fast model and deterministic fallback. Substitution/bypass can change routing and intent. | Require paired live parity evidence before changing model policy. |
| Shorten output or reduce retries | Explanation guidance already requests one to three concise claims, repair requests one short claim, and calls/output have hard bounds. Lowering bounds can cause truncation or avoidable fallback. | Preserve bounds; use repair/quality diagnostics to justify a later change. |
| Fix measurement before optimization | Route `model_calls` previously counted usage records. A provider exception could be an attempted call without a usage record. | Implement explicit boundaries and valid denominators. |

## Implementation

The evaluation route summary keeps `model_calls` as a compatibility alias for
`usage_recorded_calls`. New counters report callable attempts, normal returns and
exceptions, plus per-stage attempts and UTF-8 prompt bytes. Callable exceptions
include parsing failures after a provider response; they do not establish a
provider failure or an absence of billable usage.

Each case records the existing meter's `unknown_usage_calls` delta. Token averages
divide measured tokens by usage records with known usage. Missing usage and a zero
denominator produce `null` averages. Legacy reports that lack new counters produce
`null` attempt or known-usage counts, rather than a false zero. Recorded costs and
reservation behavior are unchanged. The evaluator hashes the new helper in its
source identity.

The wrapper counts application-level invocations. It does not observe an
unreported transport retry inside a provider library, and byte counts cannot be
used as token savings. The runtime provider adapters currently disable retries.
No live call/token baseline or savings is established by this slice.

## Verification

- Passed: nine focused diagnostics and evaluation-accounting tests; Ruff lint.
- Regressions cover a recorded parse failure, unrecorded timeout, successful
  response, returned response with unknown usage, repeated explanation calls,
  UTF-8 byte lengths, offline zeros and legacy missing denominators.
- Unchanged: runtime workflow, model rates, output/call limits, benchmark cases,
  rubric and scorer weights.
- Skipped: paid and production evaluations; no measured live gain is claimed.

## Next decision

Use the same fixed request set and source/corpus identities for paired live runs
when paid evaluation is authorized. Compare attempts, recorded usage, tokens,
repair rate and cost together with routing, grounding, fallback and latency.
Reject a reduction that merely drops requests, evidence or successful results.
