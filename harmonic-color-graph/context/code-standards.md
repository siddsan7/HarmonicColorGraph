# Code Standards

## General

- Keep modules small and single-purpose. Separate parsing,
  analysis, persistence, API wiring, scoring, and UI display.
- Fix root causes rather than layering parser exceptions or
  UI workarounds.
- Preserve original input, normalized output, warnings, and
  confidence whenever data is transformed.
- Prefer deterministic logic for theory, validation, and
  ranking. Use LLMs only at explicit boundaries.
- Add abstractions only when they remove real duplication or
  clarify a domain boundary.

## TypeScript

- Strict TypeScript is required throughout the frontend.
- Avoid `any`. Use explicit interfaces, discriminated unions,
  or narrowly scoped unknown parsing.
- Validate unknown external input before rendering it or
  sending it to another boundary.
- Keep domain types such as chords, Roman numerals, color
  profiles, and recommendations shared and stable once API
  contracts exist.
- Do not duplicate backend theory rules in frontend
  components. Render server-provided facts.

## Next.js

- This project uses Next.js 16. Read relevant local docs in
  `node_modules/next/dist/docs/` before using unfamiliar or
  recently changed APIs.
- Default to server components. Add `"use client"` only for
  browser-only interactivity such as chord input, graph
  interactions, playback, and sliders.
- Keep route handlers thin. They should validate, call a
  service, and return a typed response.
- Keep metadata accurate once the product shell is replaced:
  title and description should use Harmonic Color Graph.

## Python Backend

- Use FastAPI services with Pydantic schemas at all API and
  tool boundaries.
- Keep SQLAlchemy persistence models separate from Pydantic
  request/response schemas.
- Keep music-theory logic in `backend/app/theory/`, not in
  route handlers or database repositories.
- Use Alembic for schema migrations once PostgreSQL is added.
- Make batch ingestion idempotent where possible so sampled
  data can be reprocessed safely.

## Music Theory and Data Processing

- Canonical chord format should follow
  `<root>:<quality>/<bass_optional>`, for example `C:maj7`
  or `C:maj7/E`.
- Always preserve slash chords, parse warnings, skipped
  symbols, and unparseable raw values.
- Do not rely blindly on one parser. Use a cleanup layer,
  alias mapping, parser attempt, music21 validation, and
  explicit error reporting.
- Key detection must return confidence and possible ambiguity.
  Low-confidence cases should keep multiple analyses when
  useful.
- Roman numeral conversion must be key-aware and mode-aware.
- Emotional/color terms must be contextual and probabilistic.

## Styling

- Use CSS custom property tokens defined in `ui-context.md`.
- Avoid hardcoded hex values inside components once tokens are
  introduced.
- Follow the radius scale in `ui-context.md`.
- Build dense, useful tool screens rather than decorative
  landing pages.
- Use stable dimensions for chord chips, controls, graph
  panels, playback buttons, and score displays to avoid
  layout shift.

## API Routes

- Validate and parse request input before any business logic.
- Return consistent response shapes with explicit warnings and
  confidence fields.
- Do not expose arbitrary SQL or database internals to
  clients or LLM tools.
- Use narrow endpoints and tool wrappers:
  analysis, next-chord lookup, transition explanation,
  transition stats, recommendation, similar progressions, and
  AI query.
- Include source facts or relationship IDs in explanation
  responses when available.

## Data and Storage

- Structured metadata belongs in PostgreSQL.
- Large raw datasets, full processed corpora, notebooks
  outputs, and model files should stay local or in external
  storage unless intentionally committed as small fixtures.
- Embeddings should be stored with model name, dimensions,
  source data version, and created timestamp.
- Use small stable samples for tests.
- Never overwrite raw source data during processing.

## Testing

- Add tests before or alongside parser, analysis, scoring, and
  API work.
- Minimum Phase 1 regression cases:
  `C G Am F` -> `I V vi IV` in C major,
  `F G C` -> `IV V I`,
  `Dm G C` -> `ii V I`,
  `Fm C` -> `iv I`,
  `G Am` -> deceptive `V vi`,
  and `Db7 C` -> `bII7 I` or subV-like resolution in C.
- Track parse success, progression success, Roman confidence,
  transition counts, theory label coverage, and API latency.

## File Organization

- `app/` - Next.js routes, layouts, and UI composition.
- `context/` - Project memory and active phase context.
- `feature-specs/` - Focused implementation specs before
  building feature units.
- `backend/app/api/` - FastAPI route modules.
- `backend/app/theory/` - Chord, Roman numeral, and theory
  algorithms.
- `backend/app/services/` - Business workflows such as
  ingestion, analysis, recommendation, and explanation.
- `backend/app/db/` - Database setup, migrations, and
  repository helpers.
- `backend/tests/` - Python backend tests.
- `data/samples/` - Small fixtures that can be committed.
- `notebooks/` - Exploration only; production logic moves
  into backend modules.
