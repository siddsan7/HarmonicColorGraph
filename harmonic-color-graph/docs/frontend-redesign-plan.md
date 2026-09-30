# Frontend redesign for songwriting and music education

Updated 2026-09-29. This plan extends the initial songwriter studio proposal with an internal music education workspace. The product should help people hear, develop, and understand musical choices. A songwriter may arrive with chords, a feeling, or an unfinished section; an educator may need to inspect relationships and prepare a clear harmonic example.

## Product structure

Use two understandable entry points within one visual system: **Write music** and **Explore harmony**. Shared progression, key, genre, and section context should travel between them. Preserve existing URLs and specialist tools while improving their presentation and connection.

| Person and starting point | Intended journey | Useful outcome |
| --- | --- | --- |
| Songwriter with chords | Enter chords, listen, try a next chord or substitution, compare | Develop an idea without losing the original |
| Songwriter with a feeling | Pick a described musical direction, audition generated options, open one for editing | A playable starting sketch without needing theory vocabulary |
| Songwriter developing a song | Revisit a sketch, compare alternatives, develop sections | A coherent song sketch that can eventually be saved and exported |
| Curriculum designer or educator | Choose a harmonic starting point, inspect connections, find a route, step through and listen | A clear example of how musical functions connect |
| Internal music education product staff | Inspect context, relationship type, corpus evidence, and alternate routes | An understandable basis for lesson or product decisions |

Education is an internal authoring and inspection use case. Student accounts, grading, curriculum management, and platform integration require later product work. Keep the present interface honest about available data and actions.

## Shared visual direction

Use the character of a songwriter's studio notebook: warm ink or charcoal surfaces, cream typography, generous working space, restrained borders, and selective musical color. The graph can be denser while sharing typography, controls, spacing, and playback language with composition. Use a clear distinction between primary actions, optional settings, and evidence.

Color should communicate selection, musical qualities, and active routes consistently. A highlighted route needs a dedicated high-contrast accent that remains distinguishable from ordinary edge colors. Combine color with thickness, direction arrows, endpoint labels, and step numbers. Labels and contrast must work independently of color perception.

Motion should clarify cause and effect: a camera moving to the requested path, an inserted chord, or the current playback step. Respect reduced motion. Preserve readable labels, touch targets, visible focus, and a keyboard alternative to every graph-only action.

## Songwriter workspace

The first useful screen should invite action through three starts: **I have some chords**, **Start with a feeling**, and **Try a starting idea**. Keep the existing analysis and playback reachable. Put technical controls behind progressive disclosure; use plain descriptions with optional theory detail.

The feeling flow should initially use explicit presets mapped to existing deterministic generation controls. Let people adjust the musical direction and hear a few options. Emotional descriptions are suggestions for exploration, not objective emotional facts. Do not imply arbitrary free-text understanding unless the live assistant actually handles it. A novice can use an editable default key without first choosing one.

Keep generated results and their chord/key context connected to the editing workspace. Preserve direct chord entry, suggestions, substitutions, comparison, graph access, and MIDI export. Preserve existing shared links. The longer-term center is a persistent song sketch containing sections, chord durations, alternatives, and notes. Those additions need a deliberate document/state model; do not imply they already exist.

## Education graph workspace

Give the graph the main working area. Place a compact toolbar above it, camera controls within reach, an inspector beside it, and a visible path builder and ordered path strip adjacent to the canvas. Advanced filters and raw evidence can expand as needed. Use readable musical labels; reserve raw graph IDs for details.

The educator's core interaction is: choose a starting function and destination, find routes, select one, follow its direction, inspect each step, and audition it when realization is available. Support setting endpoints from a selected node, swapping endpoints, clearing a route, and comparing alternatives. Explain empty and unavailable results inline without discarding the current graph.

### Stable and responsive interaction

The present `GraphCanvas` destroys and recreates its Cytoscape instance whenever selection, path, color axis, graph, or callback dependencies change. Selection therefore reruns layout and fits the viewport. Refactor to a persistent instance, stable element identities, and separate data, styling, selection, and camera updates. Preserve pan, zoom, and manually moved positions when selecting or recoloring. Update existing elements in batches; place added neighbors coherently without unnecessarily moving established nodes. Relayout and fit should be explicit actions except for the first meaningful graph load.

Resize the canvas when its container changes. Provide zoom in, zoom out, fit graph, and fit path controls with accessible names. Keep interaction feedback immediate. Measure performance with representative bounded neighborhoods; do not claim a frame-rate target from a screenshot or a mocked network response.

### Clear path presentation

Use a thick, directed active route with a contrasting underlay and subdued unrelated edges. Mark the start and destination distinctly. Show the ordered route as numbered, keyboard-accessible steps outside the canvas, with selected or playing step feedback where the existing playback API supports it. Fit the route on explicit request; changing inspection should not move the camera.

Match highlighted edges by actual directed relationship identity, including relationship type and context where needed. A shared source/destination pair must not highlight an unrelated parallel relationship or reverse edge. Retain and merge every returned path edge even when its nodes are already loaded. Keep selected route edges visible despite incidental neighborhood filtering, or clearly explain the conflict. Do not merge the entire fallback corpus merely to show a short path.

Protect asynchronous path requests against out-of-order completion and changes to endpoints, filters, or context. Distinguish loading, no route, failed request, and sample data. Keep graph/list views and the path strip consistent. Evidence must remain grounded in the actual response, including missing values.

## Graph library decision

Keep **Cytoscape.js** for this implementation. Its documented element styling, batched updates, graph gestures, and viewport animation support the required interaction. The observed canvas lifecycle gives a concrete implementation defect to fix before paying migration cost. This is a reasoned choice, not a measured claim that Cytoscape outperforms other libraries. [Cytoscape documentation](https://js.cytoscape.org/)

| Option | Relevant strengths | Decision for this work |
| --- | --- | --- |
| Cytoscape.js | Existing integration; graph styling, layouts, and viewport control | Retain and substantially improve lifecycle and presentation |
| Sigma.js | WebGL rendering aimed at thousands of nodes and edges, with Graphology | Reconsider for a future large corpus map if representative profiling warrants it |
| React Flow | React node/edge customization, viewport tools, and editable diagram interactions | Consider for a future lesson authoring canvas if editing structured diagrams becomes central |

Alternative capabilities are documented in [Sigma](https://www.sigmajs.org/docs/) and [React Flow](https://reactflow.dev/learn). Their suitability judgments above are design recommendations, not benchmark results.

## UI components and motion

Keep the existing Tailwind and shadcn/Radix foundation, with custom visual tokens and deliberate component composition. [shadcn](https://ui.shadcn.com/docs) exposes editable source. Consider individual [SmoothUI](https://smoothui.dev/docs/components) components only when they improve a named interaction. [libraries.dev](https://libraries.dev/) supplies visual effects that can inform polish; effects should support the working surface. Add dependencies only for a concrete missing capability. No graph migration is currently justified.

## Implementation sequence

The authorized first implementation should make both use cases tangible:

1. Refine the shared app shell, visual tokens, and navigation around writing and exploring. Improve the songwriter entry and feeling-to-generation flow using existing services and shared progression state.
2. Rebuild graph rendering lifecycle and graph workspace hierarchy. Implement explicit camera controls, persistent selection, readable labels, and precise directed path emphasis.
3. Add the adjacent route builder, ordered steps, alternate selection, clear/swap actions, loading handling, and accessible graph/list parity. Keep playback and evidence honest about service availability.
4. Verify the core journeys, inspect desktop/mobile layouts, and record evidence and limitations. Preserve deterministic backend behavior and the existing npm/Python setup.

Later iterations can add a persisted multi-section song document, richer timing and voicing editing, saved lesson examples, embeddable education views, and platform integration. Their scope should follow feedback on the first implementation.

## Acceptance and verification

- Starting from a feeling reaches playable generated choices with no required theory knowledge; choosing one preserves its progression and key in the editing workspace.
- Starting from chords retains direct entry, analysis, suggestions, and playback. Existing shared links and specialist routes remain usable.
- Selecting a node, changing tint, or choosing an already loaded path does not recreate the graph, rerun the layout, or reset pan and zoom.
- A path is visibly directed and distinguishable from background edges. Ordered steps, endpoints, path/list state, and any playback indication agree.
- Parallel edge types and reversed edges are not falsely highlighted. Returned edges are available even when all path nodes were already present.
- Old requests cannot replace a newer context or route. Clearing or changing endpoints removes stale path state. Sample, empty, failed, and loading states are clear.
- Graph controls, route selection, and inspection have keyboard and touch alternatives. Desktop/mobile layouts avoid clipping; reduced motion is respected.
- Focused tests cover graph update stability, edge identity, route race conditions, and songwriter handoff as applicable. Run lint, typecheck, unit tests, production build, relevant Playwright journeys, and the documentation gate.
- Visually review the actual rendered canvas and path on desktop and the mobile alternative. Record what used fixtures versus live data; do not claim production corpus or playback readiness from fixture checks.

User or assigned reviewer review and required gates precede merge or deployment. Earlier M0-M7 quality and live-service gates remain open independently of this redesign.
