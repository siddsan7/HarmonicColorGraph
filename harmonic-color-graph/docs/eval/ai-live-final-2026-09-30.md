# Live AI acceptance — 2026-09-30

[Run 36800921458](https://github.com/siddsan7/HarmonicColorGraph/actions/runs/36800921458) tested commit 5fe998b with live Anthropic models and seeded domain services. All 40 cases completed at $2.497356; the $5 cap was respected and no unknown-cost cases occurred.

All configured acceptance thresholds passed:

| Metric | Result |
| --- | ---: |
| Schema / forbidden-claim checks | 1.0 |
| Intent parsing / routing / tool correctness | 1.0 |
| Theory / required tags / fact coverage | 1.0 |
| Combined intent and color direction | 0.75 (9/12) |

Twenty of the forty cases used a labeled fallback. A threshold pass does not mean every model-generated explanation succeeded. Deterministic explain-route fallback preserves registered analyzer claims with citations; candidate output remains tool-backed. The three unmet directional cases are recommend-04 (more relaxed), recommend-08 (more open), and recommend-10 (simpler). No acceptance threshold was relaxed.

This verifies live model integration against reproducible seeded tools. It does not verify the production corpus, hosted map, or listening quality. The later packaging-only commit 301b14a leaves the tested AI/ranking code unchanged. [Full machine-readable report](ai-live-final-2026-09-30.json).

[CI run 36801198105](https://github.com/siddsan7/HarmonicColorGraph/actions/runs/36801198105) on 301b14a passed backend unit, Postgres integration, frontend, documentation/tooling, and Docker Compose smoke checks, including the worker image with ML dependencies. Local backend lint, format and non-Postgres tests also passed; the local machine did not run Docker or the production Postgres integration suite.

Earlier failed runs remain recorded in the baseline, follow-up and repair reports. Total metered usage across the four live development runs was $8.152706; each run retained its independent $5 safety cap.
