# Proposed frontend design guide

Status: design proposal following the independent review, not an implemented or user-approved rebrand. Companion: [frontend design review](frontend-design-review.md). Preserve the approved 3D atlas and deterministic harmonic behavior.

## Direction: a musical observatory

Keep the product name **Harmonic Color Graph**. Use **Harmonic Atlas** for its exploration workspace. The visual direction is a precise musical instrument inside a quiet observatory: midnight surfaces, luminous musical relationships, warm route accents and occasional editorial serif emphasis. The signature comes from the relationship between notes and routes, consistent composition and thoughtful interaction.

Give the studio and graph the same shell and materials. The graph may have a deeper background and spatial grid; the editor may have denser flat surfaces. Both should clearly belong to the same instrument.

### Identity rules

- Use the existing H·G wordmark consistently while refining it into a small original mark based on two connected points. A mark exploration requires visual review before replacement.
- Use one small route motif (two or three points, a directed connecting line) in onboarding, selected ideas and exports. It must carry meaning or provide subtle identity, not occupy every panel.
- Keep amber reserved primarily for the user's active musical route or sounding selection. Use a pale blue primary action so amber state retains meaning.
- Keep informative chromatic color within data visualization. Emotional language is suggestive and editable; no hue claims a universal musical emotion.
- Reserve large editorial composition for first-use and the atlas title. Working views prioritize music and controls.

## Proposed tokens

These are starting design values, not certified contrast combinations. Validate final foreground/background pairs, including opacity, disabled controls and graph rendering before shipping.

| Role | Proposed value | Use |
|---|---|---|
| `surface.base` | `#080D16` | Application background |
| `surface.panel` | `#101927` | Forms, inspector, idea results |
| `surface.raised` | `#172438` | Menus, selection controls, dock |
| `surface.input` | `#0C1421` | Editable fields |
| `border.subtle` | `#2B3A50` | Grouping lines |
| `border.active` | `#8CAED7` | Focused/selected control boundary |
| `text.primary` | `#EEF2F8` | Headings and essential values |
| `text.secondary` | `#B6C5D9` | Body/help text |
| `text.muted` | `#91A4BD` | Secondary metadata |
| `action.primary` | `#C5D8F1` | Primary button fill, dark label |
| `route.active` | `#FFCD83` | Active path, playback position |
| `graph.cool` | `#79CFD0` | Low endpoint only when legend explains it |
| `graph.warm` | `#EFB783` | High endpoint; route also needs stroke/shape distinction |
| `state.error` | `#FF9A9D` | Error text/icon with readable container |
| `state.success` | `#91D4B5` | Confirmed successful action |
| `state.warning` | `#F0CA87` | Caution; always labeled |

Map existing application variables and shadcn semantic variables to one token source. Avoid separate neutral shadcn defaults, olive custom styles and atlas overrides drifting independently. Use semantic aliases such as `route.active`, not arbitrary one-off Tailwind colors in components. Node color data must remain separate from UI selection state.

Use 1px borders and restrained shadow only for floating layers. Panels default to 12px radius, inputs/buttons to 8px, compact chips to 6px; pills are for short tags or explicitly segmented controls. Do not make every item a rounded card: use rows and whitespace for related information.

## Typography and layout

- Keep Geist Sans for body, labels and most headings; Geist Mono for chord symbols, numerical values and short metadata. Use the existing atlas serif emphasis sparingly for one expressive word in an editorial title. Standardize its font/fallback definition before expanding it.
- Desktop editorial title: 40–48px, line-height 1.1. Working-page title: 28–32px. Mobile title: 28–34px, wrapping naturally. Panel title: 18–20px. Body: 16px/1.5. Controls: 14–16px. Metadata: 12–13px; do not use tiny monospaced text for essential explanations.
- Use a 4px spacing base with 8/12/16/24/32/48 steps. Panel padding: 20–24px desktop, 16px mobile. Related label/control gap: 6–8px.
- Shared header height roughly 60px desktop. Route-specific headers align to the same grid. Wide music/graph canvas can use nearly full width; reading content stays around 65 characters per line.
- A narrow centered form may be appropriate for a focused operation, but its title, margins and controls should still follow the same system. Remove arbitrary width changes that make routes feel unrelated.

## Information architecture

Primary tasks: **Write music**, **Explore harmony**, **Find an idea**. Similarity and Assistant remain directly accessible as supporting tools, with About in secondary navigation. Avoid changing labels without redirecting existing links and preserving keyboard discoverability.

Use one shared context line: chord summary, key and optional genre/section; an explicit action returns to editing. Say **sketch** for the current musical idea. Keep **Write music** as the route label. Use **Workbench** only if consistently presented as a named workspace; otherwise retire it from user copy.

On mobile use three primary destinations and a labeled More menu, or a clearly signaled scrollable navigation. Choose through a quick task comparison. The active destination must remain visible, including direct links to supporting tools. Do not treat invisible overflow as a discoverable menu.

### Working layout

1. Current sketch or task title.
2. Musical object: editable chord strip, candidate ideas or graph.
3. Primary action and contextual playback.
4. Optional controls.
5. Explanation and evidence on request.

First-use entry choices should transition into this working layout after selection. A repeat visitor should not repeatedly navigate onboarding. Persistence of first-use preference and sketches must be scoped explicitly.

## Component contracts

### Chord strip and sketch

Keep paste-friendly text input, paired with chord tiles for listening, replacement and ordering. Each tile exposes symbol, selected/sounding state and clear keyboard actions. Reordering needs keyboard commands as well as dragging. Retain a visible source/key summary after importing a generated idea. Undo is required before making destructive editing shortcuts prominent.

### Buttons and fields

One primary action per task region. Secondary actions use quiet outlined/tonal styles; destructive actions are labeled. Give all icon-only controls names and tooltips, while frequently used actions such as Fit graph remain visible text. Prefer 44px ergonomic targets on touch; compact desktop graph controls may be smaller if spacing and accessible target requirements are met. Labels remain visible; placeholders provide examples rather than replace labels.

Selected feeling/mode uses a check or selected label plus shape/border change. Native select semantics are acceptable when styled consistently. The same genre/key/section concepts use the same component and values across routes.

### Transport

Display the current playback source beside Play: “Current sketch,” “Idea 2,” or “Route I → IV → bVI.” Expose tempo, instrument and loop in a compact expandable area. Before playable content exists, show a short instruction in context instead of a prominent disabled transport. A playing state must be visually and programmatically distinct from a selected item.

### Idea results

Use the same result language on generator, recommendations and similarity: concise musical label, chord sequence, Play, Use in sketch and optional explanation. Show key and provenance. Preserve previous candidates while requesting a new batch; label them as previous if appropriate. Optional comparison should support listening without repeatedly shifting page position.

### Graph and inspector

Keep the 3D canvas, amber route and numbered steps. Use an active-encoding legend, clear start/destination markers and consistent node/edge selection treatment. Keep labels readable during orbit without requiring continuous animation. Hide nonessential labels progressively only with a discoverable selection/search path and accessible list equivalent.

Inspector first shows selected function and chord in current key, a concise musical explanation and the main action. Evidence follows: relationship direction, context, probability/support where available, linked facts/examples and a missing-data state. Never fabricate statistics. Explain “Add connected chords” versus “Make this the center.” Offer history for the latter.

On mobile keep a compact route summary near the graph and open endpoint editing in an accessible disclosure or sheet. Avoid permanent overlays covering nodes. Sheet dismissal restores focus. Fullscreen keeps route controls, exit and accessible equivalents available.

### Errors, loading and empty states

Use consistent cause/action language:

- Analysis: “We couldn't analyze these chords right now. Your sketch is still here.” Retry / service details.
- Generation: “New ideas couldn't load. Keep working with your previous ideas or try again.”
- Sample graph: “Sample atlas” as a compact persistent status, with readable explanation of unavailable context/counts and audio close to the affected action.
- Empty search: “No matches for these settings.” Offer the specific filter to relax.
- Assistant unavailable: “The assistant is unavailable. Continue in your sketch.” Preserve its context.

Loading retains content and marks the affected region busy. Use an indeterminate state unless there is real measurable progress. Avoid alternating multiple status messages or flashing full-page skeletons for minor edits. Technical details belong in a disclosure with a useful copy/debug action when appropriate.

## Motion

| Interaction | Proposed duration | Behavior |
|---|---:|---|
| Hover/focus/pressed | 100–140ms | Border/opacity/color; no layout movement |
| Selection or disclosure | 160–220ms | Brief fade/height transition where safe |
| Candidate insertion | 180–240ms | Small fade/translation, stable surrounding layout |
| Camera focus/fit | 350–500ms | Smooth destination with interruptible control |
| Route direction replay | 600–1000ms | One concise traversal; user can replay |

Reduced motion removes travel, camera tween and decorative interpolation while preserving final state, arrows and numbered route order. No default endless orbit or background pulse. Motion must stop consuming frames when idle. Retain existing atlas optimizations and verify any added effect on dense scenes; a beautiful sparse screenshot is insufficient performance evidence.

## Voice and musical literacy

Use concrete invitations: “Hear this idea,” “Try a darker next chord,” “Use in sketch,” “Show why.” Pair theory with explanation: “Dominant — often creates a pull toward home,” with context-sensitive qualification. Avoid absolute emotion claims, invented certainty and technical transport terms. Distinguish observed corpus frequency from recommendations and pedagogical simplification.

Translate UI-only jargon: “Structural · embedding” → “Similar movement”; “Surface · shared tokens” → “Shared chord functions”; “Unknown genre” → “Any genre” when no filter is applied. Technical terms remain available in evidence/methodology for expert staff.

## Responsive and accessibility acceptance

- Inspect at 320, 390, 768 and 1440px and at browser zoom. Canvas, headers, transport, dialogs and long chord strings require independent checks. No essential action should be obscured by a sticky region or mobile keyboard.
- Aim for 44 × 44px touch targets as product ergonomics. WCAG 2.2 AA target-size minimum is 24 × 24 CSS pixels with defined spacing/exceptions; do not conflate those rules. [W3C target-size explanation](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html).
- Validate normal text at 4.5:1 and qualifying large text at 3:1; check graph labels in the actual rendered scene and relevant control/non-text contrast separately. [W3C text contrast](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html).
- Retain visible focus, skip link, semantic headings, names for icon controls and equivalent keyboard/list access. Focus must not be entirely obscured by author-created content. [W3C focus not obscured](https://www.w3.org/WAI/WCAG22/Understanding/focus-not-obscured-minimum.html).
- Convey selected/sounding/error/route state through text or shape as well as color. Announce results and errors concisely; avoid a live announcement on every animation frame or camera movement.
- Test keyboard and screen-reader workflows manually alongside automated checks. A zero-violation automated scan does not establish full accessibility.

## What belongs to a later product specification

Saved sketches, multisection songs, persistent generation history, classroom lesson authoring and role-based platform integration need data models, recovery and permission decisions. Design them after the current end-to-end workflow is coherent. A frontend prototype must not label ephemeral state “Saved” or imply an existing classroom integration.

## Design-review gate

Before calling the next iteration polished, review actual journeys with a novice songwriter, experienced writer and education staff member. Verify successful sound, context continuity, one failure/recovery and a small-screen journey. Collect task completion and misunderstandings rather than an aesthetic approval alone. Compare rendered screenshots across all routes, including long data, unavailable services and dense graph states. Keep changes that improve the musical task and preserve the atlas's approved character.
