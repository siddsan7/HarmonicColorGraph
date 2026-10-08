# Runtime candidate integration — 2026-10-01

The public intent/preset recommender and Assistant now retrieve corpus graph
neighbors and vector discoveries. Previously, the generator supported both
sources but the session-backed service supplied neither.

Retrieval is bounded to 30 global transitions and ten neighbors for each of
five prediction seeds. Queries constrain active version, function subject,
model and major/minor mode. Scoring uses a separate batch of previous-chord
cosines for at most 64 retained candidates; discovery distance is not reused
as that feature. Candidate ordering retains theory priorities and interleaves
graph/vector discoveries before the remaining tail. Responses carry generator
provenance and do not label vector-only suggestions as theory or claim an
observed continuation count. Statistical requests retain their existing path.

## Verification

- Regression reproduced absent graph evidence before implementation.
- Fifteen focused unit tests passed, including source admission with more than
  64 candidates, previous-chord feature values, vector-only provenance, and
  no extra neighbor reads on statistical requests.
- Actual PostgreSQL 17/pgvector queries passed on a separate local test
  database with all migrations. Cases cover active-version/model/mode filters,
  missing vectors/model, and deterministic truncation of equal-distance ties.
- Full non-Postgres backend suite, lint and format passed before the final SQL
  tie-break; the focused real-Postgres test verifies that final change.
- OpenAPI and TypeScript contracts regenerated for the additive optional
  `generators` response field.

No weights were retrained and no paid model calls were made. The earlier
frozen offline hybrid report does not include this new database retrieval;
full-corpus end-to-end candidate coverage, latency and production acceptance
remain pending the corrected corpus load. Human musical quality is unreviewed.
