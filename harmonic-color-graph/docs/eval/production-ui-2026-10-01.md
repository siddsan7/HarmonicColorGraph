# Production browser verification — 2026-10-01

The public frontend was checked against the active `cv-2026-10-b` corpus, using
isolated Chromium browsers at 1440×1000 and 390×844. API revision `bd42171`
returned healthy application, PostgreSQL, and Redis status. See the
[structured evidence](production-ui-2026-10-01.json).

Both viewports loaded all 5,000 map points, returned structural and surface
similarity results with rotation labels, opened an exact mapped progression in
Workbench, and produced color profiles and recommendations without page errors.
Earlier public UI checks also exercised generator paths, comparison, playback
state, and MIDI export. A fresh exported C–G–F–C MIDI file contained 16 notes at
120 BPM with the expected pitch classes; this is not a human listening judgment.

The existing blocked-API Playwright test passed against the deployed frontend
in 4.1 seconds. Only that test browser received a simulated 503 database error;
production services were not interrupted. The published snapshot appeared,
mobile table counts matched, and I-to-bVI path search succeeded. Published asset
hashes and sizes are recorded in the [corpus report](corpus-production-2026-10-01.md).
Chordonomicon attribution is present in Workbench and evidence panels.

Automated WCAG 2 A/AA and WCAG 2.1 AA scans found no violations on `/similar`
and `/explore` at either viewport. This does not establish complete accessibility.
The map pointer-handler marks were below the browser timer resolution; they do
not measure full input-to-paint latency. Warm 150-node graph rendering measured
621.3 ms desktop and 577.9 ms mobile, but the first desktop observation was
1,319.3 ms (812 ms network). The first-load sub-second production requirement
therefore remains open. Human listening and Safari/iOS verification remain open.

## Desktop download overlap

The follow-up change starts desktop renderer downloads concurrently with the
neighborhood request. Mobile keeps its default list view and defers these
chunks. With an actual 150-node production response replayed behind an 800 ms
test delay, both renderer chunk requests started before the response; mobile
requested neither. Rendering still took 1,272.4 ms, so this removes the download
waterfall without claiming the one-second gate is met. Existing graph filtering,
path highlighting, and degraded-mode browser tests pass. Frontend lint,
typecheck, 32 unit tests and production build pass.

## First-load candidate after PR #71

The canvas component now ships with the explorer page, while the large Cytoscape
and fCOSE libraries still download only for desktop canvas view. The first
neighborhood requests 80 nodes to reduce initial clutter and layout work;
the existing expand action retains its 150-node request. This changes neither
the active corpus nor the graph API. On the optimized local production build,
five isolated Chromium runs with an actual 80-node production response delayed
800 ms reached the layout-complete mark in 937–946 ms. Five fresh contexts
using the production API through the local frontend took 200–266 ms. The
graph-filter/path and blocked-API mobile-list Playwright tests passed (2/2),
and typecheck, lint, and production build passed. The <1 s gate still needs a
measurement on the deployed frontend before it can be marked complete.

## Production first-load acceptance after PR #72

PR #72 passed independent review and all five required CI jobs, merged as
`b60222b`, and deployed READY as `dpl_4xqyXv43QJ2yyzrS2xH2S8ejeKLy`.
Five fresh desktop Chromium processes at the production alias recorded
layout-complete marks of 871.5, 207.4, 772.3, 203.6, and 201.7 ms. Every
request returned HTTP 200 with `limit=80`, the graph had 80 nodes, and there
were no page errors. All five meet the <1 s first-load target on this machine.
The earlier 1,319.3 ms observation remains a failed historical sample;
cross-device network variance is not covered by this run.

For a same-machine comparison immediately before deployment, five fresh
Chromium processes against the still-deployed 150-node page completed the
first layout in 552.9–644.1 ms, with HTTP 200 neighborhood responses and no
page errors. This confirms that the earlier 1,319.3 ms observation is not
reproducible on every first visit; it remains a recorded failed sample.
