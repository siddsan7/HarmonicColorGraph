# Frontend design review

Review date: 2026-09-30 UTC. Reviewed branch: `codex/songwriting-education-ui`, preview `http://localhost:3021`, baseline `f4c8cc6`. Scope: independent design review, no implementation changes.

## Assessment

The 3D atlas is the strongest product identity: a restrained night-sky environment, luminous relationships, clear amber routes and a recognizable editorial heading. Preserve that direction. The surrounding product still presents several independently styled utilities. The next substantial improvement should join the atlas, songwriting workflow and education workflow into a coherent instrument with reliable continuity.

The main problem is the distance between choosing an intention and hearing an editable musical idea. The current interface devotes substantial space to introductory text, inactive transport and technical controls before the user has something to work with. Professional polish also requires understandable failure recovery and clear explanation of the graph's musical meaning.

## First implementation slice

1. Fix Assistant links that drop the sketch (R01).
2. Give failed requests humane recovery while preserving work (R02).
3. Carry the approved atlas theme into the shared shell and core controls (R03).
4. Put editable music and the next action earlier in mobile songwriting/generation (R04/R10).
5. Make navigation overflow explicit and keep the active route visible (R05).

## What was actually reviewed

- Rendered all seven routes at desktop 1440 × 1000 and mobile 390 × 844: `/`, `/explore`, `/generate`, `/similar`, `/assistant`, `/about`, `/admin`.
- Exercised starter idea, Analyze, feeling selection, Generate progressions, Find similar, assistant example submission, graph path finding, route-step selection, Fit path and mobile 3D switching.
- Checked the assistant-to-workbench deep-link continuity directly. Inspected relevant component/CSS code to distinguish product behavior from service limitations.
- The local backend returned errors for analysis, generation and similarity. Assistant reported unavailability. Graph used its honestly labeled bundled snapshot. This review does **not** establish failures in harmonic algorithms or their production services.
- No network mocking was used. Successful generated results, real audio, assistant streamed answers, full-corpus graphs and authenticated admin metrics were not rendered in this review. They require a subsequent review with working services or explicitly labeled representative fixtures.
- This was a design/interaction review, not a comprehensive WCAG audit, device lab or performance benchmark. No new build/unit suite was run because only review documents changed.

Screenshots are local review evidence in `.agent-logs/review-*.png` (ignored artifacts; preserve separately if sharing the review). The full-page mobile 3D capture includes an offscreen canvas without nodes; a subsequent scrolled viewport capture verified that nodes render. This capture artifact is not a reported product defect.

## Strengths to preserve

1. The atlas has a clear visual focal point; edges recede and the selected route comes forward.
2. Numbered route steps provide a useful parallel representation of the 3D scene. List view, explicit camera controls and the statement that spatial distance is not similarity prevent common visualization mistakes.
3. The entry choices acknowledge several songwriter starting points. Feeling labels avoid claiming universal emotional meanings.
4. Advanced generation controls are disclosed progressively. The custom curve has individual keyboard-operable range controls as well as drawing.
5. The shell carries shared progression through its navigation. The graph explicitly discloses sample data and disables unavailable playback.
6. Assistant unavailable copy is more understandable than the raw transport errors elsewhere.

## Page-by-page findings

### Write music

Evidence: `review-home-desktop.png`, `review-home-mobile.png`; `components/workbench-v2.tsx`.

The desktop hierarchy is clear but the first visit offers three large choices, a disabled transport, a prefilled technical form and a second empty-state panel simultaneously. At 390 × 844 the actual chord editor is below the opening viewport. “Try a starting idea” is grouped under “03 / PLAY” but only fills the input; playback still requires successful analysis. “I have some chords” focuses the editor, which is useful, but there is little visible transition into an editing workspace.

Recommend a compact first-use entry, then an active sketch layout with the chord strip as the central object. Put the primary action beside that object and place the transport beside playable content. Keep a text editor for fast paste, paired with editable chord tiles. Make sample labels understandable by pairing “Applied dominant” with a short musical description. Use “Any genre” / “No section selected” instead of “Unknown” when the user simply has not chosen a filter.

Analyze displayed `500 Internal Server Error: Internal Server Error`. The service issue itself is outside this design finding; showing transport syntax without a recovery action is a frontend defect.

### Explore harmony

Evidence: `review-atlas-desktop.png`, `review-atlas-mobile.png`, `review-atlas-mobile-visible.png`; `components/graph-explorer.tsx`.

The atlas should anchor the visual system. Its spacious composition and concise camera dock are worth preserving. Route finding produced I → IV → bVI; step selection and Fit path were usable.

The inspector says “I” followed by “function”; a new songwriter receives little help understanding why they might choose it. Add a key-aware chord name and a short functional explanation, with carefully qualified musical language. Preserve formal identifiers under evidence. The legend says “Low tint value” / “High tint value” even when tint is Type only. It should describe the current encoding, including units or unknown values, and distinguish amber route state from high tint color.

“Expand neighbors” and “Explore from here” are different operations but their consequences are not explained. Use “Add connected chords” and “Make this the center,” with a return/history affordance. A route selector with numbered options is adequate for the sample but hard to compare at scale: show 2–3 concise route cards with step count and meaningful evidence where available. Do not invent probability, confidence or affect descriptions that the API does not supply.

On mobile, the heading, sample banner and route form occupy almost the entire opening viewport; the graph starts around y=700 before a route and moves farther down after results. Keep mobile list default as a deliberate accessibility/performance choice, but offer a compact top-level route summary and expandable route editor so visual exploration is immediately reachable. The camera dock wraps cleanly when the 3D canvas is in view. Avoid adding more permanent camera buttons.

For education staff, current controls expose a graph but do not yet form a teaching artifact. A teaching view should explain the selected relationship and let staff share a reproducible view. Saved lessons are a separate product feature with persistence and permission dependencies.

### Find an idea

Evidence: `review-generate-desktop.png`, `review-generate-mobile.png`; `components/generator.tsx`.

The three feeling options are a useful start. However, the desktop result column is mostly empty and the mobile Generate action is below the first viewport. A disabled transport appears before the feeling choice. The selected preset is mainly differentiated by a border; add a selected mark and a small visual depiction of movement/energy. Avoid decorative motion that implies an actual audio waveform before sound exists.

“Compare next chords” is a second generation workflow shown below the main generator, using an existing progression without strong visual explanation of its relationship to the current feeling. Make it a contextual action on the current sketch, or a clearly selected “New idea / Continue my sketch” mode. A small summary of key, length and chosen direction should remain visible while advanced controls are collapsed.

Generation failed with raw 500 text; its prior empty-state guidance disappeared, leaving the results heading without useful body content. Code clears paths before each request. Preserve prior successful ideas during refresh/failure and offer Retry. Successful result quality and MIDI/audio behavior were not reviewed here.

### Similar

Evidence: `review-similar-desktop.png`, `review-similar-mobile.png`.

The narrow single-column form, different heading scale and unusually large surrounding whitespace feel detached from the studio. “Structural · embedding” and “Surface · shared tokens” require implementation knowledge. Use “Similar movement” and “Shared chord functions,” then explain what each comparison measures in a disclosure.

“Embedding map — The corpus projection is not published yet” is a permanent-looking empty feature in a prime page location. Hide unavailable optional visualization or replace it with useful starter guidance; reserve diagnostics for service details. Find similar produced raw 500 text. Genre is free text here but a select elsewhere. Standardize the same concept and preserve unexpected imported values deliberately.

### Assistant

Evidence: `review-assistant-desktop.png`, `review-assistant-mobile.png`; `components/assistant.tsx`.

The composition is calmer and more considered than Similar. Example prompts are useful. Yet it behaves as a separate question box instead of assistance with the current sketch: it does not visibly show or attach the shared progression. The sidebar's “Built for listening” duplicates the main proposition while taking space that could display current musical context.

**Reproduced continuity defect:** open `/assistant?p=Am-F-C`, click “Open the workbench”; URL becomes `/` and the chord input becomes D7 - G - C. The error fallback link uses the same literal `/` in code. Preserve progression parameters on both. Assistant unavailable messaging itself is readable, but “Use deterministic tools” should become “Continue in your sketch.”

Recommend contextual prompts such as “Explain this change” and an explicit “Include current sketch” summary. Do not silently imply that the model saw a progression that was never sent. Streamed results need a separate review with realistic long answers, citations and musical actions.

### About

Evidence: `review-about-desktop.png`, `review-about-mobile.png`.

This page is mostly a description plus another current-progression card. It does little to explain the product's distinctive model or help a new user interpret musical color. Replace the duplicate card with a short, visual “How to use it” sequence, definitions of harmonic color and probability, data attribution and limitations. Include entry points for songwriters and education teams. Keep extensive research details in secondary documentation. About should be secondary navigation.

### Admin

Evidence: `review-admin-desktop.png`, `review-admin-mobile.png`; unauthenticated state only.

The credential gate is clearly marked private and reads well on mobile. It should remain a separate operations surface; it is not the education workspace. Use the same tokens and form states, but a compact operations header. Do not surface it in the main songwriter navigation. No token was entered; metrics layout, authorization and operational error states remain unverified.

## Prioritized improvement backlog

P1 = next product-quality pass; P2 = subsequent refinement; P3 = larger extension. Effort S = roughly 0.5–1 focused developer day, M = 2–4 days, L = a week or more. These are planning estimates, excluding service repair and product review. No release-blocking security/accessibility claim is implied by these design priorities.

| ID | Priority / effort | User impact and exact change | Acceptance evidence / dependency |
|---|---|---|---|
| R01 | P1 / S | Preserve sketch on both Assistant workbench links. | Am-F-C and nondefault key/genre/section survive sidebar and error recovery links; browser back remains coherent. Existing URL helpers suffice. |
| R02 | P1 / M | Replace raw 500s with action-specific errors, retained input/results, Retry and service detail disclosure. Explain disabled playback locally. | Analyze/generate/similar failures retain work, give one useful next action, and announce one concise error. Test first load and failure after prior success. |
| R03 | P1 / M | Adopt atlas-based shared tokens, header, type hierarchy and controls across every route. | Side-by-side desktop/mobile review reads as one product; shadcn semantic tokens map to the same palette; no route-wide olive→navy jump. The [design guide](frontend-design-guide.md) is the proposed source. |
| R04 | P1 / M | Make the active sketch and one primary next action central; compress first-use entry after interaction. | At 390 × 844 a returning writer reaches editable chords without scrolling through onboarding; beginner entry remains discoverable. Preserve paste and theory detail. |
| R05 | P1 / M | Provide mobile navigation with a visible overflow/menu affordance and clear active route. | All destinations reachable without discovering horizontal swipe; Assistant active state visible on direct navigation. Keyboard/focus checks. Current nav clips after Similar; horizontal scrolling exists, but its availability is not obvious. |
| R06 | P1 / M | Move inactive transport into result context; keep playable transport stable once audio exists. | No prominent dead Play before content; playing source named; changing view does not ambiguously restart audio. Needs successful audio-state review. |
| R07 | P1 / M | Make mobile atlas visible sooner via compact route summary and expandable editor. | 390 × 844 shows a meaningful graph/list preview and route entry; editing endpoints, selecting a step and inspecting evidence do not require repeated full-page travel. |
| R08 | P1 / S | Correct graph legend to actual tint/type encoding, include “unavailable” and distinct route state. | Type-only has a type legend; Tension has named low/high endpoints; highlighted route distinguishable by stroke/arrow and text as well as color. |
| R09 | P1 / M | Turn graph inspector into musical explanation with chord/function pairing and contextual evidence. | A beginner can identify selected chord in current key and what an edge means; educator can inspect provenance without leaving graph. Requires authoritative mappings and truthful missing-data copy. |
| R10 | P1 / M | Clarify generator's New idea vs Continue sketch flow; surface selected settings and keep action near choices. | Feeling→generate→listen→use in sketch forms one visible sequence desktop/mobile; no stale context or unexpected key changes. Success-state review required. |
| R11 | P2 / S | Rename technical Similar controls and remove unavailable map as main content. | Labels explain musical comparison without ML knowledge; optional missing projection does not look like broken core product. |
| R12 | P2 / M | Introduce one shared context summary and consistent terminology: sketch, key, genre, section. | Cross-route journey visibly retains context; “Workbench,” “Write music,” “sketch” no longer compete as destination names; Any/Unknown meanings are consistent. |
| R13 | P2 / M | Add contextual Assistant prompt summary and meaningful musical follow-up actions. | User can inspect exactly which sketch accompanies a question; reply can lead back to that sketch. Requires request-contract decision if context currently only embedded in prompt text. |
| R14 | P2 / M | Clarify expansion/recentering, add graph navigation history, improve alternative-route comparison. | Adding neighbors vs changing center is predictable; one action returns to previous neighborhood; route alternatives show supported differences without invented metrics. |
| R15 | P2 / M | Create unified empty/loading/partial/stale/disabled/result state components. | Each core route reviewed in all applicable states; generation leaves previous ideas visible while refreshing; skeletons resemble final content and do not fake data. |
| R16 | P2 / S | Rewrite About as concise onboarding, musical model, provenance and audience entry. | New user can explain what color and spatial position do/do not mean; attribution remains accessible sitewide. Content review required. |
| R17 | P2 / M | Tune form ergonomics and visual rhythm: shared labels, 16px input text, comfortable touch targets, consistent disclosure/selection states. | Review 320/390/768/1440px, zoom and keyboard focus; no action obscured, selected state uses more than border color. Not a claim current controls fail all criteria. |
| R18 | P2 / M | Use restrained shared motion for selection, insert/remove and scene focus; standardize reduced motion. | Motions explain changes, controls remain responsive, reduced motion has equivalent static state, no endless decorative orbit/pulses. Existing atlas motion retained where good. |
| R19 | P2 / M | Review real success results with long data and errors, then refine chord/result cards and evidence hierarchy. | Analysis, three generated ideas, similarity matches, long assistant response and full corpus view rendered on mobile/desktop. Blocked on service access or explicitly labeled fixtures for design only. |
| R20 | P3 / L | Add saved named sketches, variations, undo and section structure. | Reload/revisit preserves draft; user can branch/recover variants and distinguish verse/chorus. New product model/persistence; deliberately beyond current frontend-only scope. |
| R21 | P3 / L | Build education presentation/share view with reproducible camera/filter/path context and curated explanation. | Staff can share a bounded teaching view with accessible text/list equivalent. Saved lessons require persistence, roles and integration contract; not the same as `/admin`. |
| R22 | P3 / M–L | Refine identity assets: H·G mark, static route motif, favicon and export styling. | Identity recognizable at small size and in screenshot/export; no dependency on animated logo or ornate landing page. Brand exploration, not assumed approved renaming. |

## Recommended sequence

1. Continuity and failure recovery (R01–R02), then one design-system slice across shell, buttons, forms and headers (R03/R05/R12).
2. Finish one complete songwriter journey with real results (R04/R06/R10/R15/R19). Measure successful first listen and return-to-sketch comprehension with novice and experienced writers.
3. Refine atlas semantics and mobile ergonomics (R07–R09/R14), then observe an educator tracing and explaining a relationship without author guidance.
4. Bring Similar, Assistant and About into the same experience (R11/R13/R16–R18).
5. Scope persistence and education authoring explicitly (R20–R22); do not present those as cosmetic tasks.

Completion should be judged from real tasks: a novice starts from feeling and edits an idea; a writer brings a progression and retains it across tools; an educator explains and shares a route. Passing component tests or adding more animation alone does not establish that quality.
