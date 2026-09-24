# AI Workflow Rules

## Approach

Build Harmonic Color Graph incrementally using a
spec-driven, phase-driven workflow. Context files define what
the project is, why it exists, how the system is structured,
and what phase is active. Feature specs should define
implementation units before code is added.

The project must stay graph/theory-first. Do not jump to
LLM-first behavior just because the final product has an AI
assistant. The strongest architecture is:

```text
user intent
-> chord/key/progression analysis
-> graph/vector retrieval
-> theory and color scoring
-> validation
-> grounded explanation
-> playable UI response
```

## Phase Order

1. **Phase 1**: Data, theory, normalization, Roman analysis,
   transition graph, theory labels, and backend APIs.
2. **Phase 2**: Harmonic color profiles, embeddings,
   vector/graph retrieval, recommendation, graph UI, and
   playback.
3. **Phase 3**: LLM/RAG interface, LangGraph workflows,
   structured outputs, observability, evaluation, and
   product polish.

Do not build Phase 3 features before the Phase 1/2 data
foundation they require exists.

This three-phase framing still holds at the concept level, but
the active, numbered execution plan is
`feature-specs/v2-implementation-plan.md`'s milestones M0–M8
(see `docs/roadmap-v2.md` §7 for how they map to these phases).
Work through that plan's features (F00, F01, …) in order,
including F09, F27–F29, and F70.5. First reconcile any
chronologically skipped work, then resume the current feature
and continue through release. This file's scoping rules below
apply to each one.

## Pull Request Delivery

- All implementation changes go through a branch and a pull
  request. Use the `codex/` branch prefix by default. Do not
  make direct implementation commits on `main`.
- Choose PR size by a coherent, reviewable outcome and its
  dependencies. A feature may need multiple PRs; tightly
  coupled small features may share one PR. Keep migrations,
  application changes, tests, and documentation together when
  they form one deployable slice.
- Before opening a PR, verify the relevant acceptance checks,
  update the active plan and project context, and inspect the
  diff for secrets, generated artifacts, and unintended changes.
- Open the PR with its scope, verification evidence, migration
  or deployment impact, and known risks. Wait for required CI
  and preview checks, fix failures, then merge the PR. The user
  has authorized the implementing agent to merge PRs.
- After merge, verify the resulting `main` state and production
  behavior where applicable. Record the PR and outcome in
  `context/progress-tracker.md` and `context/HANDOFF.md`.
- Continue through features and milestones without seeking
  routine permission. Pause only for an indispensable user-only
  input or decision such as an unavailable secret, a new cost,
  or irreversible deletion. Document the blocker and continue
  independent work where possible.
- Before a session or usage limit, update the active plan,
  progress tracker, context files, and handoff with the exact
  shipped state, branch/PR state, verification, risks, and next
  actionable step.

## Scoping Rules

- Complete feature units in dependency order; split or group
  their PRs according to a coherent deployable outcome.
- Prefer small, verifiable increments over large speculative
  changes.
- Start ingestion and analysis work with small fixtures before
  full datasets.
- Do not combine unrelated system boundaries in a single
  implementation step.
- Keep frontend demos thin until backend behavior is stable.

## When to Split Work

Split an implementation step if it combines:

- Backend theory logic and frontend UI changes.
- Dataset ingestion and API route design.
- Database schema migrations and large parser rewrites.
- Multiple unrelated API endpoints.
- Phase 1 foundation work with Phase 2/3 recommendation or
  LLM orchestration.
- Behavior not clearly defined in the context files or a
  feature spec.

If a change cannot be verified within a reviewable PR, split
it along a service or acceptance boundary.

## Handling Missing Requirements

- Do not invent product behavior not defined in context files
  or feature specs.
- If a requirement is ambiguous, resolve it in the relevant
  context file before implementing.
- If a requirement is missing, add it as an open question in
  `progress-tracker.md` before continuing.
- If music-theory behavior is uncertain, prefer explicit
  warnings, confidence scores, and fixture-backed tests over
  silent assumptions.

## LLM and Agent Rules

- The LLM should not invent chord recommendations, theory
  labels, song references, statistics, or emotional claims.
- The LLM may parse user intent, call safe tools, format
  responses, and explain retrieved facts.
- Every LLM-facing tool must have a narrow schema and
  validated output.
- Explanations should use language such as "tends to feel,"
  "commonly associated with," and "in this harmonic context."
- Do not allow arbitrary SQL from model output.

## Protected Files

Do not modify the following unless explicitly instructed or
the change is required by the current feature spec:

- `node_modules/`
- `.next/`
- Large raw dataset files
- Generated model artifacts
- Third-party generated UI components if a component library
  is introduced later

## Keeping Docs in Sync

Update the relevant context file whenever implementation
changes:

- Product scope or active phase.
- System architecture or folder boundaries.
- Storage model or data model decisions.
- Code conventions or standards.
- UI patterns or design tokens.
- Feature scope, open questions, or completed work.

Update `context/progress-tracker.md` after every meaningful
implementation change.

## Before Moving to the Next Unit

1. The current unit works end to end within its defined scope.
2. Relevant tests or verification commands were run.
3. No invariant defined in `architecture.md` was violated.
4. `progress-tracker.md` reflects the completed work.
5. `npm run build` passes for frontend changes.
6. Backend tests pass for backend/theory/API changes once the
   backend exists.
7. The PR checks and preview pass, the PR is merged, and the
   resulting `main` state is verified before dependent work
   proceeds.

## Production Boundaries

- FastAPI, workers, LangGraph, and MCP orchestrate shared
  domain services; none owns a separate copy of harmonic
  business logic.
- Postgres owns durable data and job state. Redis holds
  reconstructable cache, queue coordination, rate counters,
  and other short-lived state.
- Assume repeated requests, duplicate delivery, worker
  crashes, and provider timeouts. Mutations need idempotency,
  bounded retries, recoverable leases, and inspectable failures.
- Every dependency has a timeout and an explicit degradation
  policy. Deterministic harmonic analysis must remain available
  when unrelated dependencies fail.
- A feature is not complete until trace IDs, structured error
  categories, metrics, and safe logs make its failures
  diagnosable. OpenTelemetry covers application behavior;
  optional LangSmith covers agent behavior.
