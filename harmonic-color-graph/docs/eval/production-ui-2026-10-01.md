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
