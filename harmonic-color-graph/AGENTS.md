<!-- BEGIN:nextjs-agent-rules -->
# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` before writing any code. Heed deprecation notices.

## Application Building Context

Read the following files in order before implementing
or making any architectural decision:

0. `context/HANDOFF.md` — start here. Orientation for a new
   session picking up this project: current state, established
   conventions, known gaps, and where everything below lives.
1. `context/project-overview.md` — product definition,
   goals, features, and scope
2. `context/architecture.md` — system structure,
   boundaries, storage model, and invariants
3. `context/ui-context.md` — theme, colors, typography,
   and component conventions
4. `context/code-standards.md` — implementation rules
   and conventions
5. `context/ai-workflow-rules.md` — development workflow,
   scoping rules, and delivery approach
6. `context/progress-tracker.md` — current phase,
   completed work, open questions, and next steps
7. `docs/roadmap-v2.md` — v2 product vision, verified
   current state, target architecture, and milestones
   (M0–M8); supersedes earlier roadmap documents
8. `feature-specs/v2-implementation-plan.md` — the active
   feature-by-feature build plan with acceptance checks;
   reconcile chronologically skipped features, then execute
   in dependency order, ticking checkboxes as you go
9. `context/phase-1-harmonic-data-graph-foundation.md` is
   historical (superseded by `docs/roadmap-v2.md` and the v2
   plan) — background only, not an active spec.
10. Any relevant feature spec in `feature-specs/` once
    implementation-specific specs are added.
    `feature-specs/phase-1-feature-roadmap.md` is historical
    (superseded by `feature-specs/v2-implementation-plan.md`).

Update `context/progress-tracker.md` after each
meaningful implementation change.

Use reviewable PRs for implementation changes. The user has
authorized the implementing agent to merge passing PRs and
continue across features and milestones without routine
permission requests. Choose PR size by a coherent deployable
outcome, verify CI and previews, and record merged PRs and
production checks in the progress tracker and handoff. Before
a session or usage limit, update all relevant context and the
handoff with the exact shipped state and next step. Follow
`context/ai-workflow-rules.md` for the full delivery process.

If implementation changes the architecture, scope, or
standards documented in the context files, update the
relevant file before continuing.

<!-- END:nextjs-agent-rules -->
