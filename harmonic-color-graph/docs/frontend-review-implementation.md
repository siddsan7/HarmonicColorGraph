# Frontend review implementation ledger

Scope: R01–R22 from the 2026-09-30 review, explicitly authorized together. Preserve the approved 3D atlas and deterministic services. No merge or deployment. Parent reviews before commit.

## Acceptance and verification

| IDs | Implementation contract | Required evidence |
|---|---|---|
| R01, R12, R13 | Shared musical context and explicit Assistant attachment; both recovery links and result actions retain captured context | Nondefault key/genre/section round trip; inspect submitted prompt and later edits |
| R02, R15 | Humane errors, retry, retained successful work, concise busy/stale/empty states | First failure and success-then-failure for analysis/generation/similarity |
| R03, R05, R17, R18 | One atlas-based token system, visible mobile More menu, ergonomic forms and reduced motion | 320/390/768/1440px, keyboard, zoom and automated accessibility checks |
| R04, R06, R10, R19 | Editable chord strip first, contextual transport and clear New idea/Continue sketch modes | Feeling → result → listen → edit, paste/reorder/undo; realistic long success fixtures explicitly identified |
| R07–R09, R14 | Compact mobile atlas entry, honest encoding, key-aware explanation, neighborhood history and supported route comparison | Real canvas/list, route and filter semantics preserved; no invented evidence |
| R11, R16 | Musical comparison language and concise model/provenance onboarding | Similar and About desktop/mobile content review |
| R20 | Named local sketches, sections, saved variants, undo/redo, import/export and recovery | Reload/revisit; section edits restored by undo; malformed/oversized imports rejected; URL precedence and storage failure preserve saved work |
| R21 | Reproducible bounded education presentation with curated explanation, camera/filter/path and text equivalent | Export/import or share round trip without API dependence; payload validation; explicit sample provenance; no implied platform roles |
| R22 | Original connected-point H·G identity, static route motif, favicon and print/export treatment | Small-size identity and printed/presentation view inspected |

R20 persistence is local to this browser/device, not cloud synchronization. Saved snapshots are not silently replaced by URL imports. R21 shares a validated versioned snapshot of the visible graph, not live service access or a classroom integration. Payload limits reject oversize exports explicitly rather than truncating silently.

Status: R01–R22 implemented and reviewed on 2026-09-30. No merge or deployment. User studies, live corpus access and assistive-technology lab testing remain outside the evidence below.

## Completed recommendation ledger

| ID | Delivered | Evidence |
|---|---|---|
| R01 | Both Assistant recovery/sidebar links carry chord, key, genre and section URL context | Browser context handoffs; parent final Assistant action check |
| R02 | Action-specific recovery, Retry and closed service details; previous analysis/ideas/matches remain after failed refresh; local unavailable audio explanations | Production analysis/generator success-then-failure checks; Similar unit retained-result check; real unavailable corpus review |
| R03 | Shared midnight palette, semantic shadcn/chart/sidebar aliases, working Geist font variables, coherent shell | Parent production seven-route desktop/mobile audit |
| R04 | Named active sketch, editable/reorderable chord tiles and one primary Analyze action first; starting choices and library in disclosures | 390px visual review; canonical paste, chord edit, undo and browser save journey |
| R05 | Visible native More disclosure, current secondary route label, keyboard focus styling | 320/390px audits and mobile navigation regression |
| R06 | No empty transport before playable content; active source named, settings disclosed, retained-source playback | Real analysis/audio starts; generated playback/MIDI test; repeated answer cannot reuse prior audio |
| R07 | Compact mobile route summary, expandable endpoint editor, selected ordered steps adjacent to graph/list | Mobile atlas screenshot, list/default and reduced-motion pointer selection checks |
| R08 | Type-aware legend, real numeric intervals, explicit missing readings and separate gold route state | Canvas material identity regression and legend review |
| R09 | Service-realized chord in current key plus bounded function explanation; structural facts behind disclosure | Real `/graph/realize` label; tests distinguish iii/VI, ii7 and applied functions; honest unavailable state |
| R10 | New idea/Continue my sketch modes; three selected feeling choices, near-field CTA, source-bound result/variant links | Feeling → generate → play → MIDI → sketch; variants context and retained result checks; long fixture visual review |
| R11 | Similar movement/Shared chord functions labels, methodology disclosure, optional map availability outside core results | Similar component tests and five-match desktop/mobile visual fixture |
| R12 | Shared musical context summary, consistent sketch/key/genre/section vocabulary and imported context preservation | URL round trip, saved sections and captured result context tests |
| R13 | Explicit sketch attachment, exact composed request preview and bounded counter; source-bound answer actions including Use in sketch | Assistant stream suite; repeated reply identity test; parent final action href verified with jazz/verse |
| R14 | Separate Add connected chords and Make this the center, previous-center navigation, route comparison cards with observed step/edge counts | Existing stable atlas/alternate-route suite and inspector review |
| R15 | Shared task/error/context components; retained, busy, stale, disabled and empty states; no fabricated skeleton data | Error refresh checks; section-switch stale suggestions inert and substitution actions disabled |
| R16 | About onboarding, model limits, provenance, attribution and audience entry links | Content and parent desktop/mobile review |
| R17 | 16px input text, focus treatment, comfortable touch controls, explicit selection marks, bounded scroll regions | Parent 14 route states plus teaching at 320/390/768/1440; no page overflow or main-region axe violations |
| R18 | Shared short selection/control transitions and reduced-motion override; existing finite atlas motion retained | Reduced-motion atlas and finite replay/idle suite; static alternatives remain available |
| R19 | Long successful results and real analysis reviewed | Synthetic three ideas, five eight-token Similar matches, ~1,300-character Assistant answer, five claims/citations and three candidates at 1440/390; 36/150-node graph fixtures; real analysis API success |
| R20 | Local named multi-section documents, snapshots, traced variations, undo/redo, durable recoveries and complete backup import/export | Eight hook regressions plus browser reload/variation/section/backup journey; corrupt/quota/conflicting-tab and byte-limit rejection checks |
| R21 | Versioned `/teach` capture: visible bounded graph, exact contextual directed path, selected step, tint, filters, positions/camera/target, author text and source/date; share link and JSON | Fresh browser with API blocked reproduces camera/positions/path; schema/UTF8/size/version checks; parent print and accessible-table audit |
| R22 | Original connected-point H·G mark, SVG favicon, restrained route motif and print attribution/static route | Parent visual review and readable teaching PDF/print audit |

## Verification

- Passed: lint, TypeScript, production build, 51 unit tests, documentation integrity and diff whitespace check.
- Passed: complete production Playwright run: **33 passed, 3 skipped**, followed by the four affected generator/recommendation tests passing again with explicit success-then-failure assertions. No runtime changes after the final production build.
- Passed: parent production audit of seven routes at 1440/390 (14 states), no page exceptions, document overflow or main-region axe violations. Teaching view additionally checked at 320/390/768/1440, with exact position/camera/target/path capture and readable print route/settings. Final Assistant direct action was separately re-reviewed at both widths.
- Passed: real local FastAPI analysis and playback start. Corpus generation/recommendation/similarity and Assistant success were tested using declared fixtures. Real graph service failure falls back to the clearly labeled bundled sample.
- Skipped: three live intent-ranking scenarios require an active corpus (`HCG_LIVE_RECOMMEND=1`). No backend/corpus changes, cloud synchronization, classroom roles, user study, screen-reader lab or human auditory quality claim.
- Local evidence: `.agent-logs/review-browser-production.log`, `review-unit.log`, `review-build.log`, parent production and teaching audit JSON/screenshots, `r19-review-results.json` and `r19-*` images, `atlas-36-node-path.png`, `atlas-150-node.png`, and `parent-final-action-review-results.json`. Logs/screenshots are ignored verification artifacts, not shipped product data.

## Explicit limits and recovery

Local storage has one active draft, up to 50 saved snapshots, 100 recovery drafts and 24 sections per document, with a 2 MB UTF8 total bound. Mutations are validated before state acceptance. No background cloud backup is implied. Conflicting tabs stop stale writes and offer export/reload; quota/corrupt storage preserves in-memory work and never claims it is saved. URL imports preserve the prior draft and canonical-equivalent URLs reuse the named document. An import that exceeds the bound leaves the prior book readable and writable.

Teaching captures reject more than 500 nodes, 2,000 edges or 500 KB without truncation. This bound is for a portable teaching artifact, not a renderer limit. Share links carry content in the fragment and require no local record or backend, but messaging services may reject long links; JSON export is the alternative. Captures are snapshots, never live evidence or platform authorization. Author text is rendered as text, and contextual parallel edges remain distinct. A WebGL failure still offers the relationship list. Automated accessibility checks do not establish that the visual canvas itself is fully accessible; the list, route order and relationship table provide text equivalents.
