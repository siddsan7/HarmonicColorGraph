# Minimum plausibility regret ranking experiment — 2026-10-20

The fixed candidate failed the unchanged MRR@5 gate. Runtime ranking is unchanged.
The reserved 400-position test split was not scored.

The policy applies only when every nonzero request axis has magnitude at least 0.7.
It keeps an already qualifying baseline winner. Otherwise it selects the qualifying
candidate with the greatest learned plausibility from the full existing plausibility-floor
pool. Underlying utility, then token, break ties. It moves that candidate first and retains
the other baseline top-five entries in their original order. Weak and neutral requests stay
unchanged. No model calls, database writes, weights, feature definitions, or benchmark edits
were used.

Membership was frozen before scoring: 200 development positions from 198 songs and 400
reserved test positions from 397 songs. Development and test songs are disjoint. The union
of all four registered earlier/private membership files, including their prior exclusions
and unopened reserved songs, was excluded. Protocol and source hashes are in the adjacent
protocol.json. Two string line wraps and the public registration output path were corrected
before any scoring; membership and policy were unchanged.

| Development measure | Control | Candidate |
| --- | ---: | ---: |
| Feasible directional hit rate | 60.4545% | 86.8531% |
| All-request directional hit rate | 48.0278% | 69.0000% |
| Observed-next MRR@5 | 0.539079 | 0.477060 |
| Global geometric plausibility ratio | 1 | 0.612042 |

Directional gain was 26.3986 percentage points. The paired song-bootstrap interval for that
gain was [24.8601, 27.9070] percentage points. Category regressions, neutral parity, directional
gain, and plausibility passed. MRR@5 loss was 0.062019, above the unchanged 0.02 maximum.
The candidate was rejected without tuning or opening test.

The result shows that replacing a strong request's winner with the most plausible qualifier
still loses observed-next rank under this proxy. It does not establish musical preference or
production retrieval behavior. The experiment uses local n-gram candidates and corpus data.
Source metadata and features remain frozen; no new paid evaluation was run.

Checks: five targeted boundary tests passed; Ruff lint and formatting passed; diff check passed.
The full application gates are the integrating agent's responsibility because runtime is unchanged.
