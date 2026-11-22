# Provenance and remaining metric follow-up — 2026-10-20

The supported runtime changes are a provenance false-positive fix, narrow
fallback routing recovery and request-local color-prefix reuse. Ranking and
coverage hypotheses were tested and rejected for runtime promotion. The original
benchmark, rubric, scorer, weights, vocabulary, plausibility floor, candidate cap,
provider models, timeouts and two-explanation-call limit remain unchanged.

## Provenance first

An exactly cited multiword title such as `Sample Anchor` was also extracted as
the separate subject `Anchor`. That suffix was absent from the example identity,
so the validator rejected the supported full title. The fix skips only a nested
subject already covered by the full title. The full title must still match the
exact cited example. A suffix alone, wrong citation, inferred title from an
opaque ID or unrelated second subject remains blocked.

Repair advice now gives a bounded exact example-fact-to-identity mapping using
the validator's resolver. It explicitly forbids inferring song titles or artists
from database IDs. Oversized mappings are omitted whole. Rejected prose is not
copied into repair prompts; the original prompt/headroom and call bounds apply.
No partial response is relabeled as success and fallback semantics are unchanged.
The added instructions and repair evidence have a prompt-size cost; new live
token/cost savings are not claimed.

The independent coverage worker froze twelve provenance challenges before the
parent candidate was frozen at `8e052c8`. The parent opened and scored them after
that freeze: **11/12 → 12/12**, with **zero unsupported acceptances** in either
arm. The first runner invocation stopped on an expected schema-invalid claim;
the runner was corrected to count schema rejection as invalid. Neither source
nor cases were tuned after opening. The original challenge hash is retained.
[Full challenge results](song-provenance-heldout-2026-10-20.json).

This fixes a reproduced structural bug. The rejected prose from the earlier
live `recommend-04` request was not retained, so its exact cause and the new live
fallback rate remain unverified.

## Fresh validation and remaining metrics

| Area | New evidence and disposition |
|---|---|
| Intent | Direct `create/write/compose … next chord` fallback commands now select recommendation. Valid model output is untouched. Parent-authored sealed twelve-case route holdout: **7/12 → 10/12**, zero regressions. Two constructions remain unresolved; no tuning followed this score. Original benchmark outcome remains **9/12**. |
| Directional ranking | Frozen full-pool feasibility reranker gained **1.4361 pp**, below the fixed **2 pp** minimum. Other guards passed. Rejected; runtime unchanged and reserved fresh validation remains unopened. |
| Candidate coverage | Train-only graph parity on fresh 100-song held-out cases: **1,453/1,800 → 1,453/1,800** eligible requests. Graph adds 48 candidates but no eligible coverage. Runtime already uses graph retrieval, so no source expansion shipped. |
| Completion CPU | Reuse raw color computations for each prefix. Calls fall from `n + n(n+1)/2` to `n` per key region. Four fresh contexts show **61.6–76.5%** less full-profile CPU time, exact serialized outputs; roughly **23–101 ms** saved per profile. |
| Completion median and p95 | No new live estimate. Prior controlled median is 11.728 s, above the 8 s target. CPU savings cannot establish a production tail result. Models, timeouts and failure accounting remain unchanged. |
| First candidate | Existing validated preview behavior retained; prior controlled median is 2.734 s. No new browser/production timing claim. |
| Fallback and repairs | Exact title rejection fixed and repair evidence improved. Full-draft validation, fallback labels, attempt counters and strict failures retained. No new live rate asserted. |
| Calls, tokens and cost | No added model calls or larger call budget. No new live savings claim; all work here is model-free. |

The independent route holdout was frozen before the worker candidate
`1b028c0`; worker-authored secondary validation improved 6/12 to 12/12.
The independent 10/12 result is the primary new language evidence.
[Independent cases](intent-next-chord-independent-2026-10-20.json),
[routing contract](intent-next-chord-2026-10-20.md).

Ranking development excludes all previous used/reserved experimental songs;
coverage excludes those and the concurrent ranking development/validation songs.
The coverage sample is also disjoint from its training set. These are fresh
relative to those experiments; globally untouched corpus songs are not claimed.
[Ranking protocol and rejection](feasible-ranking-2026-10-20.md),
[coverage protocol and range bounds](source-coverage-2026-10-20.md).

Coverage bounds explain **255/340 (75%)** of the remaining absent-union requests:
their fixed relative-direction threshold exceeds what the normalized feature
range permits. More candidates cannot satisfy those requests under this rubric.
This is not proof of musical impossibility. The requirement and feature semantics
were preserved; no check was weakened to manufacture a gain.

[Color reuse evidence](color-prefix-reuse-2026-10-20.md) preserves frozen
development/held-out cases, seven AB/BA timing repetitions and original output
hashes. Independent review compared four additional profiles and public
predictor/genre/section behavior against the original source exactly.

## Verification and limits

Passed before integration: 79 provenance/constraints/lifecycle tests, 116 intent
tests, 19 ranking tests, eight coverage tests and 70 color tests. Independent
review passed 109 intent/provenance/experiment tests and 33 color checks, reviewed
the held-out arithmetic and approved the integrated runtime changes.

Final backend, docs, unchanged offline benchmark and exact-head CI results are
recorded in PR78 and the shared checkpoint. Local frontend code is unchanged;
configured CI runs frontend, Postgres integration and Compose smoke gates.
Closed challenge sets are now regression evidence, not reusable tuning holdouts.
Private song membership is retained for future exclusions.

No paid model calls, production deployment, merge, corpus activation or budget
increase occurred. The weekly paid workflow stays paused. Previously reconciled
project spend is $10.668798 against the approved $12.157483 ceiling; the $1.488685
remainder cannot reserve another $1.50 pair. Live quality, production latency,
vector-source coverage and musical usefulness remain unverified. These results
do not mean that every metric in the plan improved or reached its target.
