# Bounded surprise third-slot experiment — October 20, 2026

This research-only candidate preserves the frozen adjacent policy for every
request. It adds one operation for an explicit single strong surprising request
(`common_surprising >= .7`, no other nonzero axes): if neither incumbent first
nor second meets the unchanged directional criterion but incumbent third does,
rotate `[third, first, second]`. Leave the rest fixed. Weak surprise, commonness,
other axes, mixed-axis requests, and existing matching winners keep the adjacent
policy exactly. Displacement is bounded to two positions.

The hypothesis is that an explicit rare-next-chord preference can justify a
small additional continuation tradeoff. It is not permission to weaken the
existing MRR or plausibility gates. The unchanged scorer, weights, features,
benchmark, grader, vocabulary, floor and cap remain intact. No benchmark case
outputs were inspected by the worker to select or modify this policy. The main
agent already knew the original 9/12 score and the unresolved surprise category
from the earlier audit. Adoption depends on fresh registered gates, not on a
benchmark improvement. No runtime edit is part of this experiment.

The exact source, data, protocol and 200-development/400-test memberships were
frozen before outcomes. Development has 199 songs; reserved test has 398 songs.
Every previous used or reserved song, including the independent graph challenge
and full joint, metadata and plausibility unions, is excluded. Membership and
train/development/test overlap checks apply. Cases are fresh for these
experiments; globally untouched corpus songs are not claimed.

All arms use the balanced preset and same train-only n-gram/theory/graph pool. Graph retrieval uses
global same-mode transitions at probability >= .005, stable probability/token
order and top 30, matching the previous independent graph check. Vectors are
absent. The three arms are original control, frozen adjacent ablation, and this
candidate. Both comparison labels are identifiers; intent scale remains six.

The candidate must pass every unchanged original gate against control: at least
2 percentage points feasible directional gain, no category regression above
2 points, MRR@5 loss at most .02, geometric plausibility ratio at least .5, and
identical neutral lists. It must also have strictly positive incremental
directional gain over adjacent. Failed development leaves reserved test closed.
A passing candidate may open test once; promotion additionally requires a
positive paired-song bootstrap lower bound against control. No tuning follows
measurement. This run uses no paid model calls or database writes.

## Results

The single development and registered held-out runs pass all frozen gates. No
policy, source, gate or sample changed after measurement.

| Measure | Development control | Development adjacent | Development candidate | Held-out control | Held-out adjacent | Held-out candidate |
|---|---:|---:|---:|---:|---:|---:|
| Feasible directional match | 63.0282% | 70.8451% | 71.2324% | 61.7668% | 69.7050% | 70.2845% |
| All-request match | 49.7222% | 55.8889% | 56.1944% | 48.8472% | 55.1250% | 55.5833% |
| Observed-next MRR@5 | .534389 | .518694 | .517815 | .520544 | .505405 | .504201 |

Held-out directional gain is **8.5177 percentage points against original** and
**.5796 points against adjacent**. The latter represents 33 additional matches
among 5,694 feasible requests; development had 11 additional matches among 2,840.
The held-out paired-song bootstrap 95% interval against original is
**[7.6869, 9.3640] points**, with 398 groups and 2,000 repeats. Category and neutral
guards pass. Held-out MRR loss against original is .016343, within the unchanged
.02 bound; geometric plausibility ratio is .883066, above the fixed .5 minimum.
This includes a small additional continuation-rank tradeoff against adjacent.
The positive incremental point-gain gate passes; an incremental confidence gate
was not added after seeing outcomes.

There were 7,200 held-out requests, with 5,694 feasible and 1,506 infeasible.
The candidate changes neither coverage nor the fixed feature range. It is a
small additional selection gain, not evidence that all intent requests can be
satisfied or that musician judgments improve. Twenty-eight new/current ranking
checks and Ruff lint/format pass. Frozen identity and leakage checks pass.

At measurement, this remained research-only pending independent confirmation
and review. The worker did not inspect individual benchmark outputs or edit
runtime code during the experiment. No paid calls, database writes, merges or
deployments occurred. Subsequent runtime integration is recorded below.

## Runtime integration and parity

After the fresh independent 100-song graph confirmation passed all unchanged
gates, the fixed candidate was integrated in `580c3db`. The single strong
surprise branch evaluates three incumbents even when the requested limit is one
or two. It rotates only the qualifying third, first and second candidates and
exchanges their three internal utility slots. Signed `selection_constraint`
terms record the complete adjustment; all original feature, diversity and
plausibility components remain intact. Every other request delegates exactly to
the previous adjacent policy. Balanced-preset scope and vector-neighbor/non-null
retained-similarity bypasses remain unchanged. No policy tuning followed any
measurement, and the worker did not inspect benchmark case outputs.

Runtime matches the frozen graph research operator on **9,000 requests across
all registered 400 held-out and fresh independent 100 positions**. There are
584 changed winners, including exactly **40 third-slot rotations** (the 33
registered and seven independent additional matches). All top-five token lists
match research, positions four onward are unchanged, the utility score multiset
is exact, and learned plausibility, feature values and original score components
are unchanged. Runtime helper/service hashes were unchanged throughout parity.
Registered private memberships, research source, training data, weights, scorer,
graph helper, adjacent ablation and comparison runner identities were checked.
[Runtime parity](surprise-ranking-2026-10-20/runtime-parity.json) records hashes.

Seventy-eight selection, service, HTTP, hybrid and assistant checks pass. Tests
cover utility offsets, weak/neutral/other-preset parity, existing/absent/joint
qualifiers, both vector bypass paths, descending public scores after assistant
re-sort, normalized output, exact limit 1/2/5/20 token prefixes, `[3,3,5,20]`
scorer widths for the new branch, and unchanged source evidence/fact IDs.
Ruff lint/format and diff checks pass. External services and paid models were
disabled during tests. The parity runner's initial membership-assembly NameError
was fixed before evaluating any case; runtime policy and samples were unchanged.
The parent owns the unchanged benchmark, complete repository gates and release
review. No paid calls, merge, deployment or live quality claim occurred here.
