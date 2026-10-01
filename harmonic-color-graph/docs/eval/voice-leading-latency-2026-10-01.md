# Recommendation voice-leading latency

Production PR57 smoke checks on the old active corpus measured warm recommendation
processing at 1,639–1,688 ms. Retrieval took about 15–22 ms and reranking 2–6 ms.
A local profile of 34 theory candidates attributed almost all feature-extraction
time to the voice-leading search, primarily upper-voice permutations.

Generated upper voices are ordered. Monotone matching minimizes both total and
maximum absolute motion; sorted targets also preserve the original lexicographic
tie break. The optimized path uses this property, retaining exhaustive assignment
for crossed source voices. It changes neither musical scoring nor output voicings.

Five local uninstrumented runs over the same 34 candidates measured median feature
extraction of 422.88 ms with exhaustive assignment and 184.77 ms with ordered
assignment (56% reduction). Every feature value matched exactly. This isolated
measurement is not a production latency acceptance result.

Verification: 20 focused tests passed, including exhaustive finite-grid comparisons
for all supported voice counts, duplicate pitches, crossed targets and sources,
and exact complete progression paths. Independent review approved the algorithm
and independently passed those tests. Broader backend and CI checks are recorded
with the PR. The already-running corpus build continues using its loaded code.

Evidence: `.agent-logs/voice-leading-latency.json`,
`.agent-logs/recommend-features-before.prof`, and
`.agent-logs/recommend-features-after.prof`.
