# Corrected corpus local acceptance

Passed against the frozen `cv-2026-10-b` release on local PostgreSQL 17.11 /
pgvector 0.8.2, using committed backend
`576a9657d94ad1ac48ec87bfb8314dc691f2457e`. This is not production acceptance.

The loaded manifest exactly matched frozen manifest SHA256
`35d999636616d6f5c45db8ff56c137b6720b48524042f771f633231366230605`.
All 15 norms matched their artifact values, with finite, ordered quantiles.
Stored color coverage exactly matched all 301 functions, 22,869 global
transitions, and 8,831 patterns. The default chord2vec model passed 34/40
embedding triplets (85%); FastRP remained 27/40 (67.5%).

Both function and pattern query plans used their partial HNSW indexes.
Thirty warm function-neighbor reads measured p95 **1.80 ms**. Thirty warm
structural similarity calls across three phrases measured p95 **20.16 ms**,
below the 120 ms local gate. Both `I V vi IV` and `vi IV I V` returned related,
distinct loops. The latter correctly flagged the stored canonical
`M:I M:V M:vi M:IV` as a rotation. The corpus stores one representative per
rotation class; no unstored rotational aliases are invented for a canonical
query. Filters and final top-k ranking still apply to admitted counterparts.

The original acceptance run failed rotation discovery because a noncanonical
query missed the stored pattern vector and used an approximate mean of function
vectors. Canonical lookup now uses the trained pattern vector, explicitly
considers its stored counterpart, and breaks equal-score ties by matching
length before repeated longer loops. Surface search also looks up the stored
counterpart beyond its popular-pattern shortlist.

Hybrid recommendation retrieval returned 12 graph and 12 embedding candidates;
the actual recommendation response contained at least three results and
embedding provenance. This establishes source integration, not a new frozen
hybrid-quality benchmark.

The final full load and idempotent reload passed unchanged 300 MiB `hcg` /
400 MiB database gates. Pre-activation `hcg` was 313,810,944 bytes; sampled
physical database peak was 381,761,203 bytes. Full failure, reclamation, and
old-corpus restoration are recorded in
[the storage rehearsal](corpus-storage-2026-10-01.md).

Validation: 18 focused checks including real PostgreSQL passed; the independent
reviewer reran all ten similarity/API tests successfully. Backend lint, format,
and the non-Postgres suite passed on the similarity change; the later five-line
statistics refresh passed focused loader checks. Required CI covers the final
runtime commit. Local evidence: `.agent-logs/corpus-local-acceptance.json`,
`.agent-logs/corpus-local-load-final.log`, and
`.agent-logs/similarity-materialization-plan.json`.

Real Chromium browser checks passed at 1440x1000 and 390x844 through the actual
Next.js proxy and local API, without response fixtures: 5,000 map points,
structural and surface rotation labels, exact point selection into Workbench,
color results, recommendations, and no page errors. The map test first exposed
an exact loop hidden after the picker's first 20 substring matches. Exact-case
matches now rank first, followed by case-insensitive exact matches; six component
tests pass, including a regression with 25 preceding longer matches and a
`vi`/`VI` distinction. Full frontend lint, typecheck, tests, and build passed.

All three real browser intent scenarios passed through that same proxy:
nostalgic Fm in the top five, dark/dreamy Abmaj7 in the top five, and jazz G7 in
the top three. Evidence: `.agent-logs/corpus-browser-acceptance.json`,
`.agent-logs/corpus-live-intent-final.log`, and the desktop/mobile similarity
screenshots. These are local corpus/UI checks, not deployed production results.

Production activation and HTTP acceptance, monitoring, live AI evaluation, and
human listening remain separate gates. No new paid AI evaluation was run for
these checks.
