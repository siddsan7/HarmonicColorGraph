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

## Scoping Rules

- Work on one feature unit at a time.
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

If a change cannot be verified end to end quickly, the scope
is too broad; split it.

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
