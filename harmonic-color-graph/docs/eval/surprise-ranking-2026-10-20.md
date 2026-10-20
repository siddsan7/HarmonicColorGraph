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
outputs were inspected to select or modify this policy. No runtime edit is part
of this experiment.

The exact source, data, protocol and 200-development/400-test memberships were
frozen before outcomes. Development has 199 songs; reserved test has 398 songs.
Every previous used or reserved song, including the independent graph challenge
and full joint, metadata and plausibility unions, is excluded. Membership and
train/development/test overlap checks apply. Cases are fresh for these
experiments; globally untouched corpus songs are not claimed.

All arms use the same train-only n-gram/theory/graph pool. Graph retrieval uses
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
