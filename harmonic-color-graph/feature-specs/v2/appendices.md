## Stretch (after v1.0; not required)

| ID | Feature | Note |
|---|---|---|
| S1 | Neo4j/AuraDB export | `hcg-build export-neo4j` writes CSV plus Cypher `LOAD CSV` scripts from the same artifacts; demo Bloom perspective. |
| S2 | DSPy optimization of the intent parser | Needs the F76 benchmark as the metric. |
| S3 | Genre-specific agent presets | R&B / film / jazz / pop / gospel weight presets and example sets (Phase 3 §14.5). |
| S4 | Hooktheory comparison | Only if API access and terms allow (Phase 1 §4.2). |
| S5 | Audio chord extraction | Essentia or similar (Phase 3 §14.4). |
| S6 | DAW bridge | Web MIDI out to a DAW (Phase 3 §14.2). |

---

## Traceability: phase documents → features

| Phase doc section | Features |
|---|---|
| P1 §4 data sources (Chordonomicon, music21) | F20–F21, F11/F12 oracle (ADR-004); Hooktheory → S4 |
| P1 §5–§6 absolute + relative model, entities | F10, F12, F23 |
| P1 §7 database schema | F05, F23 (+ F43, F51, F73) |
| P1 §8 chord normalization | F10 |
| P1 §9 Roman conversion, key detection, ambiguity | F11, F12 |
| P1 §10 theory labels | F13 |
| P1 §11 API (`analyze`, `next-chords`, `explain-transition`, `transition-stats`) | F04 (v1), F14, F25, F32 |
| P1 §12 step 10 tests | F03 → flipped in F11–F13 |
| P1 §13 quality metrics | F21, F31 |
| P1 §14 minimal frontend | F07, F14 |
| P2 §4–§5 color axes, probabilistic emotion | F41, F42 |
| P2 §6.1 rule-based scores | F42 |
| P2 §6.2 corpus-based scores (commonness, surprise, genre distribution) | F22, F41 |
| P2 §6.3 voice-leading scores | F40, F41 |
| P2 §6.4 progression aggregation | F43 |
| P2 §7 embeddings (chord, progression, graph) | F50 |
| P2 §8 vector database | F51 |
| P2 §9 recommendation engine | F52, F54 |
| P2 §10 progression builder, radar, graph, playback | F44, F54, F61–F64 |
| P2 §12 evaluation (theory, corpus, listening) | F41 checks, F31, F82 |
| P2 §14 demo scenarios | F54 acceptance tests |
| P3 §4 LangChain/LangGraph/LangSmith/Ragas/DSPy | F71, F75, F76, S2 |
| P3 §6 LangGraph workflow and branching | F71 |
| P3 §7 tools | F70 |
| P3 §8 RAG over structured facts | F13 facts, F23 `facts`, F70, F72 |
| P3 §9 structured output schema | F71 |
| P3 §10 AI UI (prompt, cards, compare, explorer, explanation mode) | F74, F64, F63 |
| P3 §11 evaluation | F76, F82 |
| P3 §12 observability | F73, F75 |
| P3 §13 honesty rules | F13 lint, F42, F72 |
| P3 §14 advanced (MIDI, taste profile, RLHF, agents, audio, DAW) | F64, F81, F80, S3, S5, S6 |
| P3 §15 deployment | F05–F08 |
| P3 §16–§17 demo script and resume bullets | F84 |
| P3 §19 definition of done | M7/M8 exit gates, F85 |

---

## Appendix A — Kickoff prompt for Claude Code

```text
Read AGENTS.md and follow its read order, including docs/roadmap-v2.md and
feature-specs/v2-implementation-plan.md. Execute the plan starting at the first
unchecked feature. Work one feature at a time on its own branch. After each
feature run the Standard Check Gate (§0.4) and the feature's acceptance checks,
update context/progress-tracker.md with the results, tick the checkboxes, open a
PR, and wait for CI to be green before merging. Record evidence at each milestone exit gate and continue to the next
feature without waiting for a milestone confirmation. Ask only for indispensable inputs in §0.2 and before an action that
costs money or deletes remote data. Continue independent work while waiting.
```

## Appendix B — Storage budget worksheet (update after F22/F24)

| Table | Estimate | Measured |
|---|---|---|
| nodes | ~5 MB | |
| edges (all types and contexts) | ~60 MB | |
| ngram_histories | ~120 MB | |
| patterns + examples + song_refs | ~40 MB | |
| color_profiles + norms | ~20 MB | |
| embeddings + HNSW | ~25 MB | |
| facts, logs, app tables | ~15 MB | |
| **Total `hcg` (target ≤ 300 MB)** | **~285 MB** | |

Overflow playbook (ADR-007): raise the n-gram pruning thresholds → drop the `decade` × order-3 contexts → move `ngram_histories` to a zstd-compressed artifact in Supabase Storage loaded per warm instance → Supabase Pro (needs approval).


## Appendix C — Production architecture principles

The implementation agents should follow these rules throughout the project.

## 1. Interfaces orchestrate; domain services own business logic

> **FastAPI, workers, LangGraph, and MCP are interfaces/orchestrators around shared domain services. Business logic should not be duplicated inside any of them.**

Bad:

```text
FastAPI recommendation algorithm
+
worker recommendation algorithm
+
MCP recommendation algorithm
```

Good:

```text
recommendation service
        ↑
 ┌──────┼───────┐
FastAPI Worker  MCP
```

---

## 2. Durable truth and ephemeral state must remain separate

> **Postgres owns durable truth. Redis owns ephemeral coordination. Workers own durable asynchronous execution.**

Use Postgres for:

```text
harmonic data
graph
facts
users
jobs
evaluations
AI logs
feedback
persistent results
```

Use Redis for:

```text
cache
rate limits
queue internals
temporary state
locks
ephemeral progress
```

---

## 3. LLMs are not the source of harmonic truth

> **LLMs explain and orchestrate; deterministic systems remain responsible for harmonic facts and scoring.**

The LLM may:

```text
interpret user intent
choose tools
summarize evidence
generate natural-language explanations
```

The LLM should not independently invent:

```text
transition probabilities
Roman analysis
voice-leading scores
graph relationships
color values
evidence
```

Those come from deterministic services and retrieved facts.

---

## 4. Design for at-least-once execution

Assume:

```text
HTTP requests can be repeated
queue jobs can be delivered more than once
workers can crash
external services can time out
```

Therefore:

```text
mutations must be idempotent
retries must be bounded
side effects must be versioned/upsert-safe
failed work must become inspectable
```

---

## 5. Graceful degradation is preferable to total failure

Where possible:

```text
LLM unavailable
→ deterministic recommendation still works

Redis unavailable
→ uncached read path still works

embedding subsystem unavailable
→ graph/statistical ranking still works

Postgres unavailable
→ DB-free theory analysis still works
```

The system should make dependency boundaries visible rather than collapsing the entire application when one subsystem fails.

---

## 6. Observability is part of correctness

A production feature is not complete if failures cannot be diagnosed.

Every major path should expose enough telemetry to answer:

```text
What failed?
Where did it fail?
How long did it take?
Was it retried?
Which corpus/model version was used?
How much did the AI call cost?
Did the system fall back?
```

This is why OpenTelemetry, structured logs, trace IDs, job IDs, and LangSmith are part of the architecture rather than optional debugging extras.

---
