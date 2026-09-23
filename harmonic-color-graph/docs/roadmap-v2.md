# Harmonic Color Graph — Roadmap v2 (Supabase + Vercel)

> Revision 2 — 2026-09-23. Replaces the previous roadmap in this Project.
> Companion document: `harmonic-color-graph-implementation-plan.md` (feature-by-feature build plan with checks).
> Source-of-vision documents: `phase_1_harmonic_data_graph_foundation.md`, `phase_2_color_embeddings_recommendation_engine.md`, `phase_3_llm_agents_productization.md`.

---

## 0. What changed in this revision (and why)

The previous roadmap diagnosed the Phase 1 code well (first-order prediction, weak key detection, no `V/x`, no color layer, no graph UI) and its core sequencing instinct — *fix analysis before learning anything from it* — is kept. This revision changes it where it drifted from the three phase documents, missed live defects, or ignored the chosen infrastructure.

| # | Previous roadmap | Problem | Revision |
|---|---|---|---|
| 1 | Neo4j becomes the harmonic-intelligence layer. | Contradicts Phase 2 (pgvector first, Neo4j optional) and Phase 3 deployment (Supabase/Postgres + pgvector). Adds a third managed service whose free tier also pauses. The derived graph is small (~10k nodes, hundreds of thousands of edges): it does not need a graph engine. | **Postgres property graph in Supabase** (typed `nodes`/`edges` tables + pgvector) with graph algorithms (paths, FastRP/Node2Vec, communities) computed in Python. The pipeline writes a neutral node/edge artifact, so a **Neo4j export stays an optional stretch** (ADR-002). |
| 2 | "Current state" lists the transition lookup as "implemented, but shallow". | **It returns wrong numbers.** Contextual rows are keyed by genre+subgenre+section+decade and never re-aggregated, so a lookup returns duplicate candidates with inflated probabilities, and unfiltered queries mix global rows, contextual rows, and major/minor modes. Reproduced (§2.2). | Correctness hotfix in the first milestone; proper per-context marginals in the corpus build. |
| 3 | Key detection is flagged "partial". | Understated. Chordonomicon has **no key column**, and the ingester estimates a key **per section**, so 35% of sections get a different key than their own song, and 93% of confidence scores sit at the 0.95 cap. Roman numerals across the corpus are inconsistent. | Song-level 24-key probabilistic key finding with section-level modulation detection, calibrated confidence. |
| 4 | Harmonic color is Phase 7 of 10. | Color is the product's namesake and the core of Phase 2. The measurable axes (tension, chromaticity, brightness, surprise, smoothness) are cheap deterministic functions. | Measurable color features land **right after prediction v2** (M4) and feed the recommender and UI from then on. Subjective axes follow, always with `confidence` and `source`. |
| 5 | Graph UI and playback are Phase 9. | No demoable product until the very end; the phase docs ship UI with every phase. | **Deploy a vertical slice in M0** and grow the UI with each capability. Playback arrives with voice leading (M4 to M6). |
| 6 | Deployment is barely mentioned. | You asked for a fully working product on Supabase + Vercel. | M0 deploys the API and web app to Vercel with preview deploys on every PR, plus a keep-alive against Supabase free-plan pausing. |
| 7 | Phase 3 is one paragraph. | Missing: LangGraph node design and branching, structured outputs, grounding validator, observability, evaluation (tool-call, faithfulness, human), rate limiting and cost control, recruiter packaging. | Full M7/M8 milestones mirroring Phase 3 §3–§19. |
| 8 | Phase 2 items missing. | No Word2Vec chord embeddings, progression embeddings, intent sliders, compare mode, radar display, listening study, or feedback loop. | All included (M4–M6, M8). |
| 9 | No realization layer. | Recommendations exist as Roman numerals; nobody converts them back to correctly spelled, voiced, playable chords in the user's key. | `realize()` + voice-leading engine are first-class features. |
| 10 | "Check the license." | Checked: **Chordonomicon is CC BY-NC 4.0.** | Portfolio and non-commercial use are fine, with attribution in the UI and README. Commercial use needs different data (out of scope). |
| 11 | Storage: "don't dump raw data into Postgres." | Right idea, no numbers. The June `DiskFull` failure came from the free plan's storage limits (**500 MB database quota, 1 GB disk**). | Explicit storage budget (≤ 300 MB), measured at every load, with a documented fallback. |
| 12 | No per-feature verification. | You asked for checks after every feature. | The implementation plan defines a standard gate plus feature-specific acceptance checks. |

---

## 1. Product vision (merged from Phases 1–3)

**Harmonic Color Graph is a graph/vector harmonic-intelligence engine that maps chords, functions, transitions, progressions, context (genre, section, era), and harmonic color. Creators can explore it as a graph, get context-aware, explainable, playable recommendations, and shape progressions by intent. A grounded AI assistant sits on top and never invents musical truth.**

The Epicure analogy still anchors the design:

| Flavor domain | Harmonic Color Graph |
|---|---|
| Ingredients | Chords (absolute) and functions (Roman, key-relative) |
| Recipes | Songs, sections, progression patterns |
| Co-occurrence | Transition and n-gram statistics |
| Food chemistry | Music theory: intervals, voice leading, function |
| Flavor axes | Harmonic color axes (measurable + perceptual) |
| Pairing predictor | Next-chord recommender, substitution finder, generator |
| LLM interface | Tool-using, fact-citing harmonic assistant |

### 1.1 Product definition of done

The product is done when a visitor to the production URL can:

1. Enter a progression (or nothing) and get **key analysis with honest ambiguity**, functional Roman numerals (`V7/vi`, `iv`, `bVII`, `viiø7`), and labeled relationships.
2. Get **context-aware next-chord recommendations** that change with the whole progression, genre, and section, each with a score breakdown, evidence counts, and real example songs (Spotify links).
3. Steer recommendations with **intent sliders** (darker/brighter, common/surprising, simple/complex, resolved/open, smooth) and see how each candidate changes the color profile.
4. **Explore the harmonic graph visually**: neighborhoods, typed relationships, filters, paths between chords ("I → bVI, increasingly chromatic"), and similar functions and progressions.
5. **Find substitutes** and **generate multi-chord progressions** under constraints (length, cadence, tension curve, color target).
6. **Hear everything**: voice-led playback, A/B/C compare, loop, tempo, MIDI export.
7. **Ask in natural language** ("make this more nostalgic but still resolved") and get validated, playable, fact-cited answers.
8. See the **evaluation evidence**: prediction metrics against baselines, color sanity suites, AI faithfulness and tool-call metrics, and listening-study results.

---

## 2. Verified current state (2026-09-23)

### 2.1 What exists

| Area | State | Evidence |
|---|---|---|
| Repo | `siddsan7/HarmonicColorGraph`, `main` at `32191dc` (2026-06-15), 24 commits, all Phase 1. The local clone matches GitHub. | `git log` |
| Backend | FastAPI: `/health`, `/analyze-progression`, `/next-chords`, `/explain-transition`, `/transition-stats`. | `backend/app/api/phase1.py` |
| Tests | **57** test functions (the runbook says 50). No CI, so nothing proves they pass. | `grep -c "def test_"` |
| Chord parsing | Solid: 99.99% token success on a 5k-row sample (per tracker). Canonical `root:quality/bass`. | `theory/chord_normalizer.py` |
| Key/Roman analysis | Home-grown heuristic. Root-candidate keys only, semitone-to-numeral map, no applied chords, extensions and inversions dropped, `dim` renders as `VII`. `music21` is a dependency but unused. | `theory/roman_analysis.py` |
| Relationship labels | ~10 hard-coded patterns; major-mode uppercase forms only (no `V→i`, no `bVI→bVII→I`). | `theory/relationships.py` |
| Database | SQLAlchemy + Alembic schema, also applied to Supabase through MCP (two migration systems). `roman_chords`, `theory_labels`, and `transition_theory_labels` are never written. | `models/harmony.py` |
| Supabase | Project `HarmonicColorGraph` (`bqaateqbbavwnbyfuqvk`, us-west-2) is **INACTIVE (paused)**. The full-provenance seed hit the free plan's storage limits (`DiskFull`) and rolled back; the `--transition-only` seed never ran. The free plan allows restore for **90 days** after pausing, so the window may have closed. | Supabase MCP, progress tracker |
| Vercel | **No HarmonicColorGraph project** (the account has my-tune, portfolio, beatpad, truckerpath*). | Vercel MCP |
| Frontend | One-page Phase 1 workbench (`components/phase-one-demo.tsx`) calling `localhost:8000`. No graph view, no playback. | |
| CI | None. | no `.github/` |

### 2.2 Defects reproduced against the real code

Run with the repo's own modules:

```text
Dm G          (no key)  -> G major, v -> I        conf 0.95   expected: ii -> V in C (ambiguous)
D7 G C        (C major) -> II7 V I                           expected: V7/V V I, "secondary dominant"
E7 Am         (C major) -> III7 vi, no labels                expected: V7/vi vi
Fm C          (no key)  -> "F major", i -> V                 expected: iv -> I in C (borrowed)
Bdim C        (C major) -> VII I                             expected: vii° I
Cmaj9 Fadd9 Gsus4 C     -> I IV V I (extensions lost)
Am Dm E7 Am   (no key)  -> i iv V7 i, no labels             expected: authentic cadence in minor
Ab Bb C       (C major) -> bVI bVII I, no labels            expected: Aeolian/"Mario" cadence, modal mixture
C Am F G      (no key)  -> C major 0.95, A minor alt 0.95   confidence ties, primary still claims 0.95
```

Transition lookup (5 fixture progressions, query `I,V,vi`):

```text
genre=pop, section=chorus -> [IV 1.0, IV 1.0, IV 1.0, ii 1.0]      duplicates, probabilities > true values
no filter                 -> [IV 1.0, IV 1.0, IV 1.0, IV 1.0, ii 1.0, iii 1.0, IV 0.5, ...]
I-V-vi vs ii-V-vi         -> identical rankings (first-order only)
```

### 2.3 Corpus profile (full Chordonomicon v2 CSV, measured)

| Metric | Value | Design consequence |
|---|---|---|
| Songs | 679,807 | |
| Sections | 2,952,684 (median 12 chords, p90 33) | |
| Chord tokens | 51,994,634; 4,314 distinct symbols | |
| Adjacent identical chords | 0.01% | Repeats are already collapsed; nothing to do. |
| Duplicate sections within a song | **23.9%** (e.g. `verse_2 == verse_1`) | Deduplicate per song (keep a repetition weight) or counts skew toward repeated material; required for leak-free evaluation. |
| Songs without `main_genre` | 48% | Genre-conditioned models need backoff; show "unknown genre" honestly. |
| Songs without decade | 38% | Era filters are partial. |
| Songs with Spotify ID | 64.8% | Evidence panel links to Spotify; titles come from Spotify oEmbed (the dataset has no titles and anonymized artists). |
| Section keys ≠ song key (current analyzer) | **34.6%** | Analyze keys per song, detect modulations per section. |
| Confidence at the 0.95 cap | **92.8%** | Confidence is currently meaningless. |
| Current analyzer throughput | ~1,200 sections/s/core | A full corpus pass is ~40 min single-core; parallelize. |
| n-gram types with count ≥ 5 (v1 vocab, extrapolated to full corpus) | order 3 ≈ 70k, order 4 ≈ 240k, order 5 ≈ 400k | Store n-grams as one row per *history* with a JSONB next-distribution, prune by order, and enforce the storage budget. |

---

## 3. Target architecture

```text
                    Chordonomicon v2 CSV (CC BY-NC 4.0)  [+ future sources]
                                   |
                    OFFLINE BUILD PIPELINE  (Python, Polars, multiprocessing)
      parse -> song-level key + local keys -> functional Roman v2 -> labels
      -> dedupe sections -> aggregates (transitions per context, n-gram histories,
         patterns, examples) -> color features -> embeddings (Word2Vec, FastRP)
      -> Parquet artifacts + manifest (versioned, hashed, reproducible)
                                   |
                   LOADER (COPY, versioned, atomic swap, size-checked)
                                   v
   SUPABASE (Postgres 17, schema `hcg`, RLS on, not exposed via Data API)
     property graph: nodes / edges (typed)   n-gram histories   patterns + examples
     color_profiles   embeddings (pgvector, HNSW)   facts (grounding)   corpus_versions
     app data: feedback, saved_progressions (Auth), ai_query_logs, rate_limits
                                   |
   VERCEL project "harmonic-color-graph-api"  — FastAPI (Python 3.12, fluid compute)
     /v1/* (legacy baseline)   /v2/analyze  /v2/recommend-next-chords  /v2/find-substitutes
     /v2/generate-progression  /v2/similar-*  /v2/graph/*  /v2/color/*  /v2/examples
     /v2/ai/query (LangGraph + Claude, SSE)   /health, /health/db
                                   |
   VERCEL project "harmonic-color-graph"  — Next.js 16 (rewrites /api/hcg/* -> API)
     Workbench | Graph Explorer (Cytoscape) | Generator | Similarity | Assistant | About/Eval
     Tone.js voice-led playback, compare mode, MIDI export
```

### 3.1 Architecture decisions (ADRs, to be committed under `docs/adr/`)

- **ADR-001 Offline build, online serve.** Nothing heavy runs in a request: the corpus pass, aggregation, embeddings, and color percentiles are batch jobs. The API reads compact derived tables. Pipeline dependencies (Polars, gensim, music21, scipy) live in optional extras and never enter the Vercel bundle.
- **ADR-002 Postgres property graph instead of Neo4j.** `hcg.nodes(id, type, label, props)` and `hcg.edges(src, dst, type, context_id, count, prob, weight, props)` with per-type partial indexes. Multi-hop queries are ≤ 2-hop SQL; path search (Yen k-shortest, constrained beam) runs in Python over a cached in-memory subgraph (a few MB). Embeddings live in pgvector. *Revisit if* the graph needs ad-hoc Cypher exploration by non-developers, or the edge count passes ~5M. The stretch feature S1 exports the same artifact to Neo4j/AuraDB.
- **ADR-003 Function tokens are mode-aware and two-level.** Every chord gets a `figure` (full: `V65/V`, `IVmaj9`, `viiø7`) and a `core` token used as the graph vertex (`M:V7/V`, `M:IV`, `m:VII`, where `M`/`m` is the local mode). Absolute chord identity is always preserved alongside.
- **ADR-004 music21 is an oracle, not a runtime dependency.** Analysis v2 is implemented in-house (fast, small bundle, fully tested). music21 cross-checks the gold set in a dev-only script.
- **ADR-005 Single migration system.** SQL files in `supabase/migrations/` are the source of truth (applied through Supabase MCP or CLI, and in CI against a `pgvector/pgvector:pg17` container). Alembic is retired.
- **ADR-006 LLM is an interface, never an oracle.** LangGraph in the FastAPI service, Claude via `langchain-anthropic` (model set in env), safe typed tools only, Pydantic-validated structured outputs, and fact-ID citation enforced by a validator node.
- **ADR-007 Storage budget.** Free plan: 500 MB database. Target ≤ 300 MB for `hcg` including indexes, checked after every load. Overflow options, in order: tighten pruning → move n-gram histories to a compressed artifact in Supabase Storage loaded by the API → upgrade to Pro (your decision).
- **ADR-008 Licensing.** Chordonomicon is CC BY-NC 4.0: attribution in the footer, About page, and README; the project stays non-commercial (also required by Vercel Hobby). The corpus manifest records license per source.

### 3.2 Deployment topology

- **Two Vercel projects from one repo:** `harmonic-color-graph` (root `harmonic-color-graph/`, Next.js) and `harmonic-color-graph-api` (root `harmonic-color-graph/backend/`, FastAPI zero-config). The web app proxies `/api/hcg/*` to the API through a rewrite: same-origin in the browser, no CORS in production, and the API URL stays server-side.
- **Supabase:** restore `bqaateqbbavwnbyfuqvk` if it is still in the 90-day window, otherwise create a new free project in the same org. Connect through the **transaction pooler** (port 6543) with SQLAlchemy `NullPool` and psycopg `prepare_threshold=None` (serverless-safe).
- **Keep-alive:** a daily Vercel Cron (Hobby allows daily) calls `/health/db`, which runs a real query. The UI degrades to a read-only static graph snapshot if the database is unreachable.
- **CI/CD:** GitHub Actions (backend tests including Postgres integration, frontend lint/typecheck/build, OpenAPI type drift check). Vercel Git integration creates preview deployments per PR and production on `main`.

---

## 4. Data model

### 4.1 Graph (in `hcg`)

**Node types:** `PitchClass`(12) · `Interval`(12) · `ChordQuality` · `Chord` (absolute, ~4–5k) · `Key`(24) · `Function` (mode-aware core tokens, several hundred) · `Genre` · `Section` · `Era` · `Pattern` (frequent loops/phrases, ~50k after pruning) · `RelationshipType` · `ColorAxis`.

**Edge types:**

| Class | Edges |
|---|---|
| Structural | `HAS_ROOT`, `HAS_BASS`, `HAS_QUALITY`, `CONTAINS_PC`, `FUNCTIONS_AS` (Chord→Function, count), `IN_MODE` |
| Statistical | `TRANSITIONS_TO` (Function→Function, per context: count, prob, PMI, support), `ABS_TRANSITIONS_TO` (Chord→Chord, global, pruned), `PATTERN_CONTAINS` (position), `COMMON_IN` (Pattern→Genre/Section, lift) |
| Theory | `RESOLVES_TO`, `SECONDARY_DOMINANT_OF`, `APPLIED_LT_OF`, `BORROWED_FROM`, `TRITONE_SUB_FOR`, `CHROMATIC_MEDIANT_WITH`, `RELATIVE_OF`, `PARALLEL_OF`, `COMMON_TONE_WITH` |
| Voice leading | `VOICE_LEADS_TO` (min total motion, common tones, parsimonious move) |
| Similarity/color | `SIMILAR_TO` (embedding kNN, materialized top-k), `COLOR_SIMILAR_TO`, `DARKER_THAN` / `MORE_TENSE_THAN` (derived, for explanations) |

**Contexts** (`hcg.contexts`): `global`, `genre:<g>`, `section:<s>`, `decade:<d>`, `genre×section` (pruned to cells with enough support). Every statistical edge carries `context_id` and `corpus_version`.

### 4.2 Other tables

- `ngram_histories(context_id, order, history, total, next jsonb)`: one row per history, distribution in JSONB.
- `patterns`, `pattern_examples(pattern_id, song_ref_id, section, position)`, `song_refs(id, source_id, spotify_id, genre, decade)` (only songs referenced as examples).
- `color_profiles(subject_type, subject_id, context_id, axes…, confidence jsonb, source, version)`.
- `embeddings(subject_type, subject_id, model, dim, vec vector(64))` with an HNSW cosine index.
- `facts(fact_id, kind, subject, template, params jsonb)`: stable IDs the AI layer cites (`rule:modal_interchange`, `transition:M:iv->M:I:global`).
- `corpus_versions(version, manifest jsonb, active bool, loaded_at)`.
- App: `feedback`, `saved_progressions` (RLS by `auth.uid()`), `ai_query_logs`, `rate_limits`.

---

## 5. Capability specs (summary; details in the implementation plan)

**Analysis v2.** 24-key scoring from duration-weighted chord pitch-class profiles plus cadence evidence, softmax-calibrated. Song-level key plus per-section local keys (modulation when a section's own key wins by a margin). Functional labeling: diatonic, secondary dominants `V(7)/x`, applied leading-tone `vii°(7)/x`, modal mixture with source mode, Neapolitan, tritone substitutes `subV/x`, chromatic mediants; inversion figures and extensions preserved; T/PD/D function class. Ambiguity is returned, never hidden.

**Prediction v2.** Interpolated Kneser-Ney over core tokens (orders ≤ 5) with context backoff (genre×section → genre → section → global) and a transparent per-order contribution breakdown. `realize(token, key)` returns spelled absolute chords.

**Harmonic color.** *Measurable* (0–1, corpus-percentile normalized): tension, stability, chromaticity, brightness (line-of-fifths position relative to tonic), surprise (−log P in context), smoothness (voice-leading cost), complexity, resolution tendency, finality. *Perceptual* (nostalgia, dreaminess, melancholy, warmth, openness, cinematic) are documented combinations of measurable features plus curated rules (Phase 2 §6.1), each with `confidence` and `source`. Language is always probabilistic ("tends to feel…").

**Recommendation.** Candidates from n-grams, graph neighbors, theory expansions (applied dominants, borrowed chords, tritone subs, mediants), and embedding neighbors. The score combines a *plausibility* model (logistic regression on held-out songs) with a user-controlled *intent* term; every feature's contribution is returned.

**Generation.** Constrained beam search: hard constraints (length, key, start/end, cadence, chromaticity cap, required chords) and soft objectives (tension curves, color targets, novelty), returning diverse paths with per-step explanations.

**AI assistant (Phase 3).** LangGraph workflow: Intent → Parse/Analyze → Route (recommend | explain | generate | similar | compare) → Retrieve (graph | vector | theory) → Color score → Validate → Rank → Explain → Format playback → Final. Structured output with `claims[{text, fact_ids}]`; the validator rejects any chord not produced by a tool or any claim without a fact. SSE streaming, rate limiting, cost cap, logs, optional LangSmith.

---

## 6. Evaluation framework

| Layer | Metrics | Gate |
|---|---|---|
| Parsing | token and progression parse rate, top unparseables | ≥ 99.9% tokens |
| Key/Roman | accuracy on the gold set (≥ 60 curated cases), top-2 accuracy, ECE calibration, music21 agreement | ≥ 90% top-2, ECE < 0.10 |
| Labels | per-rule unit tests (both modes); corpus coverage | ≥ 60% of transitions labeled |
| Prediction | top-1/3/5, MRR, NDCG@5, perplexity, coverage, calibration; per genre/section; **song-level split** | v2 MRR > v1 MRR with a clear margin; context sensitivity test passes |
| Color | Phase 2 §12.1 sanity suite (V→I resolution, V→vi surprise, iv→I darkness/nostalgia, bVI–bVII–I cinematic, I–iii–vi smoothness) | 100% of suite orderings hold |
| Recommender | accuracy retention vs n-gram, novelty, diversity, intent-shift success rate | intent success ≥ 80% on 30 inputs |
| Generation | constraint satisfaction, curve correlation | 100% hard constraints; ρ ≥ 0.7 |
| AI | routing accuracy, JSON validity, tool-call correctness, fact coverage (faithfulness), adversarial must-not suite; optional Ragas | 100% schema-valid; 100% must-not; ≥ 90% routing |
| Human | listening study (20 progressions × 5 intents × 3–5 raters), explanation clarity 1–5 | reported, not gated |

---

## 7. Milestones

| Milestone | Theme | Phase-doc coverage | Outcome |
|---|---|---|---|
| **M0** Foundation & deploy skeleton | CI, baseline goldens, lookup hotfix, Supabase restored/created, single migration system, API + web on Vercel, keep-alive | Roadmap Phase 0; P3 §15 | Existing app is live, measured, and protected by CI. |
| **M1** Harmonic analysis v2 | chord features, 24-key finder, functional Roman v2, relationship catalog v2, `/v2/analyze` + UI | P1 §8–§10, §12 steps 3–7 | Analysis is trustworthy enough to learn from. |
| **M2** Corpus pipeline & harmonic graph | manifest, full-corpus build, aggregates, graph schema, loader, graph APIs, evidence | P1 §4–§7, §13; P2 §7.4 | The project becomes a real harmonic graph in Supabase. |
| **M3** Prediction v2 | KN n-grams with context backoff, realization, evaluation harness, `/v2/recommend` | Roadmap P4; P1 §11 `/next-chords` | Predictions depend on the whole progression and are measured. |
| **M4** Color & voice leading | voice-leading engine, measurable + perceptual color, color storage, color UI | P2 §4–§6, §10.2 | The "color" in Harmonic Color Graph exists and is explainable. |
| **M5** Embeddings, similarity & hybrid recommender | Word2Vec + FastRP, pgvector search, candidates + hybrid scorer, substitutes, intent sliders | P2 §7–§9, §11; Roadmap P5–P6 | Recommendations by creative intent, with similarity search. |
| **M6** Generation, graph explorer & playback | beam-search generator, Tone.js engine, app shell, Cytoscape explorer, generator/compare/MIDI, similarity map | P2 §10; Roadmap P8–P9 | It feels like a harmonic graph database you can play. |
| **M7** Grounded AI assistant | tools, LangGraph workflow, validator, streaming endpoint + limits, assistant UI, observability, AI eval | P3 §3–§12 | Natural-language control, grounded and evaluated. |
| **M8** Feedback, accounts, polish & launch | feedback loop, saved progressions + taste profile, listening study, performance/resilience, docs, release | P3 §13–§20; P2 §12.3 | Recruiter-ready v1.0 in production. |

Stretch (not required for done): **S1** Neo4j/AuraDB export · **S2** DSPy intent-parser optimization · **S3** genre-specific agent presets · **S4** Hooktheory comparison · **S5** audio chord extraction · **S6** DAW/MIDI-out bridge.

---

## 8. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Supabase project past its restore window | M0 creates a fresh project; nothing of value is in the old one (the seed rolled back). |
| Free-plan pausing takes the demo down | Daily keep-alive cron + static snapshot fallback + clear status banner. |
| 500 MB cap | Budget, pruning, history-row n-grams, size check on every load, Storage fallback. |
| Analysis errors pollute everything downstream | Gold set + calibration gates before the full corpus build; the build is re-runnable. |
| Serverless bundle or cold-start limits | Runtime deps kept minimal; pipeline deps in extras; bundle-size check in the deploy gate. |
| Recommendations become opaque | Score breakdowns, facts, and evidence required in every response schema. |
| Emotional overclaiming | Perceptual axes carry confidence/source; language lint test; the validator blocks absolute claims. |
| LLM cost or abuse on a public demo | Rate limiting, daily budget cap, cheap model for intent parsing, deterministic fallback. |
| Licensing | CC BY-NC attribution; non-commercial positioning; manifest tracks licenses. |
| Scope creep | Milestone gates; stretch items stay stretch. |

---

## 9. Immediate next tickets

1. F00–F02: plan docs into the repo, hygiene, CI.
2. F03–F04: v1 golden snapshot + transition lookup hotfix.
3. F05: Supabase restore-or-create, `hcg` schema, SQL migrations as the single system.
4. F06–F08: API and web on Vercel, keep-alive.
5. F11–F12: 24-key finder and functional Roman v2 (the gate for everything else).

Shortest path to a product that is visibly better:
**CI → deploy skeleton → analysis v2 → corpus build → graph + prediction v2 → color → hybrid recommender → explorer + playback → assistant.**
