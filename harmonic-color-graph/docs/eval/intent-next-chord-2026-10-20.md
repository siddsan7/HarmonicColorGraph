# Direct next-chord fallback intent — October 20, 2026

The fallback parser treated `generate the next chord` as progression generation.
The generic verb won before the explicit next-chord object. Generation then
discarded the directional request. Recover direct `generate/create/make/write/
compose [me] [a/the] next chord` commands as recommendation requests. Earlier
explain/compare/similar priorities stay intact. Valid model output stays
authoritative. Negated, alternative, quoted and mixed whole-progression requests
do not activate this recovery. Missing chords still require clarification.

This correction improves a fallback routing contract. It does not establish an
improvement in the existing recommendation-outcome metric. Reproduction with the
unchanged seeded pool still identifies two infeasible cases (04, 10) and one
ranking tradeoff (05); recommendation parsing remains 12/12 and outcome 9/12.
The paired live intent score likewise combines parsing and selected color, so
its unchanged 5/6 cannot justify overriding valid model output.

The worker froze six development and twelve separate validation cases before
baseline scoring and runtime edits. SHA256 identities and exact outputs are in
[baseline](intent-next-chord-2026-10-20/baseline.json) and
[candidate](intent-next-chord-2026-10-20/candidate.json). Exact route-plus-axis
matches improve from 3/6 to 6/6 in development and 6/12 to 12/12 in validation.
The worker authored both sets, so this is a fresh frozen secondary validation,
not independently authored evidence. The integration agent has a separate
unseen frozen sample and will score the committed candidate once. No tuning
will follow that score. Published cases become regression cases.

Integration result: the parent-authored twelve-case sample, frozen before the
worker candidate, scored **7/12 → 10/12** with zero regressions. No tuning followed
that score. This independent result is primary; the worker's 12/12 is secondary.
[Independent frozen evidence](intent-next-chord-independent-2026-10-20.json).

The generator accepts absolute `[0,1]` targets, while assistant intent axes
express signed relative directions. No product contract defines the reference
or conversion. Generator mapping remains unchanged; inventing an absolute
target here would alter musical search without supporting evidence.

Checks: 116 focused fallback/expansion/workflow tests pass; Ruff check/format pass.
There are no paid calls, scorer changes, benchmark/rubric edits or release actions.
Production outcome, broader natural-language understanding and musical usefulness
remain unverified. The integration agent owns full benchmark and release gates.
