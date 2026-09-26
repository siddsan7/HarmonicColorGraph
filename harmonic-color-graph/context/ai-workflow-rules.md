# AI workflow and delivery

## Scope and context

Use AGENTS.md, the current handoff, and the relevant milestone specification.
Search the documentation index when additional context is needed. Implement
authorized features in dependency order, retaining F00–F85 identifiers,
including F09, F27–F29, and F70.5. Do not start unrelated milestones merely
because their plan exists. Original workflow history is archived under
`history/2026-09-26/ai-workflow-rules.md`.

Keep the product graph/theory-first: analyze, retrieve, score, validate, explain,
and return a playable result. Ground explanations in retrieved evidence.
Typed tools validate inputs and outputs; no arbitrary model-authored SQL.
Shared domain services own business logic. Postgres owns durable state and
Redis reconstructable state. Preserve timeout, retry, idempotency, and lease
semantics. Consult architecture and ADRs when changing these boundaries.

## Implementation

Match process to the task. A lookup needs a focused read. A substantial feature
needs acceptance criteria and one working slice early. A bug needs a small
reproduction and a falsifiable hypothesis. After two distinct failed approaches,
reassess evidence and context rather than repeatedly rewriting the same code.
Use the existing lockfile, tools, and conventions. Do not edit generated/vendor
files, raw datasets, or large artifacts except when the requested task requires it.

## Verification and PRs

1. Use a `codex/` branch and a PR for implementation. A coherent outcome can
   span backend, frontend, tests, and migrations when they depend on each other.
2. Run focused checks while implementing. At the PR boundary, run relevant
   `scripts/check.py` scopes and all feature acceptance checks. Full product
   releases require the release scope, configured integration dependencies,
   applicable infrastructure checks, and green required CI/previews.
3. Review actual behavior and the diff. Record pass/fail/skip evidence and
   limitations. Never weaken a test to make it pass. A golden-data change needs
   a documented musical reason. A skipped integration test is not a passed one.
4. Open a PR with scope, evidence, and migration/deployment impact.
5. **Before merge or deployment, obtain review by the user or an explicitly
   assigned reviewer.** The implementing agent's own verification is insufficient.
   Existing authorization to continue applies after this review and required
   checks. Do not merge a failing PR.
6. After an authorized merge, verify the resulting main/deployment as relevant
   and update the compact handoff. Keep completed detail in linked history.

Use an independent reviewer for consequential changes when assigned. Give the
reviewer requirements, diff, and test evidence; request concrete failure cases.
Do not routinely create multiple agents or councils for trivial changes.

## Continuity and operational limits

Update current state at a meaningful checkpoint, blocker, or session handoff.
Update architecture, facts, diagrams, and standards only when their described
behavior changes. Do not copy the same history into every context file.
When blocked, record the missing input and continue independent work.

New costs and remote destructive actions require explicit authorization.
Treat full-corpus reloads as separately scoped operations. Keep credentials in
local ignored configuration. Preserve meaningful trace IDs and safe diagnostic
evidence; production telemetry and Codex build-time usage are separate systems.
