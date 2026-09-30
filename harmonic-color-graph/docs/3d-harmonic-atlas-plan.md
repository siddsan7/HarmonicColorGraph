# 3D harmonic atlas

## Goal and reference

Build a visually striking, futuristic graph for songwriters and music education staff, with genuine depth, clear directed paths, concise animation and approachable controls. This supersedes the earlier decision to keep Cytoscape for the primary canvas. Preserve existing deterministic analysis, route identity, context, playback and songwriter handoffs.

Reference inspected: [Epicure](https://epicure.kaikaku.ai/about). Its dark expansive atlas, restrained editorial typography, colored spatial clusters, fine connections and compact controls inform the composition. Its ingredient embedding geometry does not imply that our harmonic layout is an embedding: label ours as a relationship layout and avoid claims that distance is a measured musical similarity.

## Visual and interaction specification

- Give the graph the dominant surface: midnight ink, restrained cyan/iris/amber light, hairline borders and translucent compact tools. Harmonize the surrounding route builder and inspector. No decorative dashboard metrics.
- Real 3D nodes and curved directed connections, with depth cues, selective labels, luminous selection rings and a subtle spatial reference. Labels must remain readable. Small sample graphs should look intentionally composed; dense neighborhoods should stay navigable.
- Drag to orbit, wheel/pinch to zoom, an explicit pan gesture, reset/fit graph, focus selected and fit route. Expose clear labeled buttons and a brief controls guide; no required gesture knowledge.
- Stable graph and camera throughout inspection, tint changes and path alternatives. Data updates preserve existing positions. Bound physics settling; no endless drifting or default automatic rotation.
- Paths use a contrasting luminous stroke, arrows, emphasized endpoints and ordered steps. Brief travel particles illustrate direction; a replay control makes it intentional. Parallel/reversed/contextual links must retain exact identities.
- Camera transitions approximately 300–600ms; hover response immediate. Respect reduced motion, suspend offscreen/hidden rendering where feasible and clean up GPU resources. No constant gratuitous animation.
- Keep accessible list and numbered route navigation. WebGL failure offers a useful fallback. Touch/mobile layout must preserve controls, content and route selection without horizontal overflow.

## Implementation choice

Use [3d-force-graph](https://github.com/vasturiano/3d-force-graph), a Three.js graph renderer, for its orbit camera, custom node geometry, curved links, arrows, particles and incremental data updates. Lazy-load the renderer; retain the React workspace and graph data contract. Isolate rendering and pure presentation helpers so graph semantics are testable without WebGL. Add only needed dependencies using the existing npm lockfile.

## Build sequence

1. Replace primary canvas with a persistent typed 3D renderer and deterministic initial positions, custom materials/labels and stable data updates.
2. Compose the atlas workspace, selection details, camera controls and path animation. Preserve the earlier songwriter and education journeys.
3. Test edge identity and layout helpers; verify real browser orbit/zoom/focus/reset, pointer selection, path direction, camera persistence, keyboard/list, reduced motion, mobile and WebGL failure.
4. Inspect actual desktop/mobile screenshots and a meaningful dense fixture, then refine spacing, contrast, depth and labels. Run lint, typecheck, unit tests, production build and focused browser regressions. Capture evidence and limitations.

## Completion criteria

The primary graph is demonstrably 3D and its camera can orbit. A selected path is immediately traceable and directed, including parallel/contextual edges. Controls work without hunting through settings. Selection/tint/path updates preserve the scene. The desktop composition looks deliberately designed, and mobile/keyboard alternatives remain usable. No runtime errors, leaked render loops or failing focused checks remain. Actual rendered review, interaction checks and measured bounded dense-fixture behavior accompany the handoff; green tests alone do not establish visual quality. Live service availability and large-corpus performance are reported separately. No merge or deployment without review.

## Implementation and acceptance evidence — 2026-09-29

The primary canvas now uses lazy-loaded `3d-force-graph` and Three.js. The Epicure reference and upstream renderer documentation informed the composition and API choice; the renderer is an actual perspective scene with nonzero z coordinates, raycast selection and an orbit camera. Cytoscape and its unused types were removed. Songwriter entry, captured generation context, deterministic services, shareable URLs and route semantics remain intact.

Implemented and inspected:

- Midnight atlas shell, luminous musical color, selective readable labels, curved directed connections, compact camera tools and full-screen exploration. The workspace states that relationship-layout distance is not a measured similarity score.
- Exact directed/type/context edge identity, contrasting route materials and arrows, ordered clickable steps, endpoints, alternates, clear/swap and existing request guards. Tests inspect actual node materials and link style accessors, rather than only echoed route props.
- Persistent scene and retained node positions/camera during inspection, tint and route changes. New nodes settle in a bounded deterministic layout; unchanged topology skips settling. All graph nodes remain available: there is no hidden display truncation.
- Brief cancellable directional replay, reduced-motion behavior, idle/offscreen/hidden rendering suspension, resize handling, resource disposal on eviction and unmount, and usable WebGL failure/List view fallback.
- Real mouse orbit and pointer raycast selection, focus/zoom/reset/fit, native full-screen enter/exit, and mobile controls/List navigation. Visual iterations fixed tiny labels, excessive empty framing, stale endpoint tint, background label collisions, theme seams, reduced-motion camera matrix updates, and fitted camera limits that prevented idle suspension on a wider 150-node graph.

Verification:

- Passed ESLint, TypeScript, 39 Vitest tests, production Next.js build, documentation integrity and final whitespace check.
- Passed 17 focused Chromium journeys against the production build: 11 graph journeys plus generation/comparison/playback/MIDI, captured-context songwriter handoff, shared URLs/mobile navigation and database-unavailable regression. Graph coverage includes exact path materials, stale requests, 36-node/68-edge rendering, real orbit/raycast/fullscreen, reduced-motion mobile, WebGL failure, repeated mount/list replacement and a 150-node/434-edge idle/wake check, plus repeated zoom-to-limit checks.
- Reviewed actual production screenshots: `.agent-logs/atlas-36-node-path.png`, `atlas-mobile.png`, `atlas-fullscreen.png` and `atlas-orbit.png`. Parent independently reviewed the sample graph, desktop/mobile composition and route readability. Parent's automated accessibility scan of the main region found zero violations; this does not establish visual canvas accessibility, which also relies on List view and ordered route navigation.
- Synthetic layout measurements in the full unit run: 150 nodes 42.8ms, 300 nodes 80.9ms and 1000 nodes 81.0ms; corresponding stable updates 0.4ms, 0.6ms and 1.4ms. Above 300 nodes deterministic sampled repulsion bounds solver work. These are local CPU layout observations, not GPU frame-rate claims or a production corpus benchmark.

Skipped: merge, deployment, corpus/backend changes and unrelated M0–M7 release gates. Browser network responses use explicit fixtures or the bundled sample fallback; live graph API/realization availability, full production corpus performance and subjective musical usefulness remain unverified. Parent owns the final checkpoint and independent review record.

Independent dense interaction review: headless Chromium at 1440x1000 with a synthetic 150-node/434-edge fixture, offsets 1/4/11 and varied chromaticity. A real 60-step pointer orbit produced 182 RAF samples: median 33.3ms, p95 33.4ms, maximum 66.7ms (about 30fps in this environment). The same probe before optimizing background links and hover work measured about 4fps. The scene started idle and returned to idle. Background connections now use lightweight GL lines; route connections retain thick geometry/arrows. Hover changes label sprites without rebuilding graph-wide link geometry. These measurements are bounded local headless-browser evidence, not a universal device or corpus performance guarantee.
