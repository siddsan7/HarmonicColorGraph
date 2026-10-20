# Adjacent-swap ranking — October 20, 2026

This fixed policy bounds ranking displacement directly. For a strong request,
when the current winner fails and its incumbent runner-up satisfies every requested
axis, swap only those two candidates. Keep all top-five members and the other
three positions unchanged. Otherwise return the original list. Neutral and weak
requests are identical. No extra plausibility ratio or intent-scale sweep applies.

The earlier full-pool constraint improved directional agreement but failed the
unchanged MRR guard. This new objective limits rank distortion to one adjacent
pair. Source, protocol, and fresh 200-development/400-test memberships were frozen
before outcomes. New development has 200 songs; reserved test has 397 songs.
Every earlier experimental membership, the concurrent coverage sample, and the
independent 100-song challenge are excluded, including their reserved members.
No train/development/test song overlap is allowed.

All existing gates remain unchanged: at least 2 percentage points feasible
agreement gain, no category loss above 2 points, MRR@5 loss at most .02,
geometric plausibility ratio at least .5, and identical neutral lists. Reserved
test opens only after passing development; promotion also requires a positive
paired-song bootstrap lower bound. Same 18 requests, .025 criterion, scorer,
weights, feature definitions, plausibility floor, and 64-candidate cap apply.
Both arms use intent scale6; label8 only identifies the candidate.

This is model-free research on the local n-gram/theory pool. It is not a
production graph/vector or listener evaluation. No runtime order or score change
is shipped without separate score-contract review. No paid calls or database
writes occur. Failed development leaves reserved validation closed.
