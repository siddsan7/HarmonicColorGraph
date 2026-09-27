# Progress — current summary

## Active

- Product: M7 F70, F70.5, and F71 merged after independent reviews. F72
  grounding validator and adversarial suite are in implementation.
- Harness: Current owner and exact next action are in the root resume packet.
- [Product context](HANDOFF.md) preserves M5 caveats and historical pointers.

## Completed milestones

M0–M5 merged; F60 generator checks cover 200 constrained requests, 30 curve
seeds, path diversity, and p95 latency. Detailed feature checkboxes are in the corresponding
[milestone files](../feature-specs/v2-implementation-plan.md). F54 shipped in
PR #27 (`fbc7c65`); M5 documentation closed in PR #28 (`55722f5`).

M6 F65 is merged via PR #36. Real-corpus UMAP publication, live similarity,
and F61 manual listening remain pending. M7 F70 adds ten internal tools with
input/output JSON schemas and evidence envelopes. Local F70 checks passed:
26 focused tool tests after review fixes; backend lint, format, and unit suite; frontend lint,
typecheck, tests, and build; documentation integrity. Thirteen Postgres tests
skipped because no local test database is configured. PR #37's first CI run
passed; independent review found three tool-boundary gaps, fixed at 5544fbe.
The reviewer approved that head; PR CI run 36297200286 passed all five jobs,
both Vercel previews passed, main CI run 36297344909 passed, and production
API `/health` returned 200 at merge commit cb3dd66. F70.5's in-process MCP
client discovers ten tools and checks direct-output parity; stdio and local
Streamable HTTP clients both complete round trips. F70.5 backend lint, format,
and unit suite; frontend lint, typecheck, tests, and build; documentation
integrity all passed locally. Thirteen Postgres tests skipped without a local
test database. Independent review approved head 832d9f7; PR #38 CI run
36297867978 passed all five jobs and both Vercel previews passed. PR #38
merged at 77dd5c8; main CI run 36298009682 passed and production API health
returned HTTP 200 at that version. F71 merged via PR #39 at 341b595 after
independent review, passing all PR CI and preview checks. Main CI run
36299595516 passed. Its LangGraph has ten
nodes, six routes, tool-sourced candidates/facts, model response repair, and
deterministic fallback. A local 20-query full-graph suite routes 20/20
correctly; fixture-backed response, key ambiguity, export, and citation tests
pass. F71 backend lint, format, and unit suite; frontend lint, typecheck,
tests, and build; documentation integrity all pass locally. Thirteen local
Postgres tests skip without a test database. Live Claude evaluation awaits
`ANTHROPIC_API_KEY`; the referenced Phase 3 §5 prompt source is unavailable
in this checkout. F72 adds five grounding rules and a 30-case adversarial
corpus with an optional cost-accounting real-model runner. Focused validator,
workflow, language, and corpus integrity tests pass.

## Pending human evidence

Siddharth's three manual listening comparisons remain open; see the handoff.
Do not mark subjective checks completed from automated tests.

## History

The [complete previous tracker](history/2026-09-26/progress-tracker.md) preserves
all completed entries and metrics. Append a short outcome here at a meaningful
checkpoint, then archive accumulated detail; avoid duplicating feature reports.
