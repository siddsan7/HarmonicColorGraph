# Harmonic Color Graph

[![CI](https://github.com/siddsan7/HarmonicColorGraph/actions/workflows/ci.yml/badge.svg)](https://github.com/siddsan7/HarmonicColorGraph/actions/workflows/ci.yml)

Harmonic Color Graph is a harmonic intelligence workbench for
analyzing chord progressions, converting them into Roman
numerals, labeling harmonic relationships, and recommending
next chords from a corpus-backed transition graph.

The project is intentionally graph/theory-first. LLM features
come later, after the symbolic music and data foundation can
produce grounded, inspectable results.

## Current Phase

Phase 1 is the data, theory, and graph foundation.

Implemented:

- FastAPI backend for harmonic analysis.
- Chord and progression normalization.
- Key-aware Roman numeral analysis.
- Rule-based harmonic relationship labels.
- Supabase/Postgres schema for chords, songs, progressions,
  transitions, labels, and metadata.
- Full-library-capable Chordonomicon CSV/JSONL seed command.
- Database-backed `/next-chords` and `/transition-stats`
  endpoints with explicit demo fallback.
- Next.js Phase 1 demo UI.

## Project Shape

```text
harmonic-color-graph/
  app/                    Next.js App Router shell
  components/             UI components and Phase 1 workbench
  backend/                FastAPI, theory, ingestion, database code
  context/                Persistent project memory
  data/                   Local raw/processed/sample data
  docs/                   Runbooks and implementation plans
  feature-specs/          Phase implementation roadmaps
  notebooks/              Dataset inspection notes
```

## Quick Start

For a local full stack with Postgres, Redis, API, worker bootstrap, and
frontend, see [the Docker runbook](docs/runbooks/docker.md). Copy
`.env.docker.example` to `.env.docker`, set the local database password
in both `POSTGRES_PASSWORD` and `DATABASE_URL`, then run
`docker compose up --build -d`. Open `http://127.0.0.1:3000` and check
`http://127.0.0.1:8000/health`. Docker and Compose v2 are required.

To run the services separately without Docker:

Install frontend dependencies:

```powershell
npm install
```

Install backend dependencies:

```powershell
cd backend
$env:TEMP='C:\tmp'
$env:TMP='C:\tmp'
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" -m pip install --user -e ".[dev]"
```

Run backend:

```powershell
cd backend
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Run frontend:

```powershell
npm run dev -- --hostname 127.0.0.1 --port 3000
```

Open:

```text
http://127.0.0.1:3000
```

## Supabase And Corpus Seeding

See [docs/phase-1-runbook.md](docs/phase-1-runbook.md) for:

- Supabase project details.
- `DATABASE_URL` setup.
- Full-library Chordonomicon CSV ingestion.
- Metrics output.
- Demo fallback behavior.
- Backend/frontend verification commands.

## Useful Backend Commands

Run all backend tests:

```powershell
cd backend
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" -m pytest
```

Seed the Chordonomicon v2 CSV corpus into the configured database:

```powershell
cd backend
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" -m app.ingestion.seed_corpus ..\data\raw\chordonomicon_v2.csv --reset-database --metrics-output ..\data\processed\phase1_quality_metrics.json --batch-size 1000
```

Analyze a progression:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/analyze-progression -ContentType 'application/json' -Body '{"chords":["C","G","Am"],"key":"C major"}'
```

Look up next chords:

```powershell
Invoke-RestMethod 'http://127.0.0.1:8000/next-chords?progression=I,V,vi&genre=pop&section=chorus'
```

## Typed Harmonic Tools

The M7 assistant uses ten validated internal tools in `backend/app/ai/tools.py`.
They call the same domain services as the API without making HTTP requests.
Analysis, color, and playback work without a corpus database; corpus-backed
tools need a request-scoped database session. Every result includes typed
`data`, `fact_ids`, and `evidence`. Empty `fact_ids` means the service has no
stored fact to cite; callers must not invent one. The examples tool assigns
stable `example:*` IDs to exact returned corpus rows so later validators can
check song citations against those rows.

```python
from app.ai.tools import HarmonicTools
from app.db.session import create_session_factory

session_factory = create_session_factory()
with session_factory() as session:
    tools = HarmonicTools.from_session(session)
    result = tools.call(
        "recommend_next",
        {"progression": ["C", "Am", "Dm"], "key": "C major", "limit": 3},
    )
    print(result.model_dump())
```

From `backend/`, export all input and output JSON schemas with
`python -m app.ai.schemas > ai-tool-schemas.json`. Tool calls raise `ToolError`
with stable codes for invalid input, missing corpus data, unavailable database,
and invalid output.

### MCP clients

The MCP server publishes those same schemas and results. From `backend/`,
`python -m app.mcp.server` runs the stdio transport for a local MCP client.
Configure the client to launch that command with `backend/` as its working
directory. For a local Streamable HTTP endpoint, run:

```powershell
cd backend
python -m uvicorn app.mcp.server:app --host 127.0.0.1 --port 8001
```

An MCP client can then call a database-independent tool:

```python
import asyncio
from mcp import Client

async def main():
    async with Client("http://127.0.0.1:8001/mcp") as client:
        print([tool.name for tool in (await client.list_tools()).tools])
        result = await client.call_tool(
            "analyze_progression", {"chords": ["C", "G", "Am"], "key": "C major"}
        )
        print(result.structured_content)

asyncio.run(main())
```

Corpus-backed tools use the configured `DATABASE_URL`. MCP returns structured
tool errors for invalid harmonic input and does not accept SQL, file paths, or
administrative operations.

### Assistant workflow

F71 compiles a LangGraph workflow over the same typed tools. Set
`ANTHROPIC_API_KEY` to use Claude for intent parsing and grounded explanations;
`HCG_LLM_FAST_MODEL` and `HCG_LLM_MODEL` override the default model IDs. With
the key absent or a model response invalid, the workflow uses bounded
deterministic parsing and explanation. From `backend/`:

```python
from app.ai.tools import HarmonicTools
from app.ai.workflow import AssistantWorkflow
from app.db.session import create_session_factory

with create_session_factory()() as session:
    workflow = AssistantWorkflow.from_environment(HarmonicTools.from_session(session))
    response = workflow.run("Recommend the next chord after C G Am in C major")
    print(response.model_dump(mode="json"))
```

The response contains tool-sourced candidates and facts, any competing key
analyses, optional playback, and a `fallback` flag. F72 validates every model
claim against tool fact IDs, chord and Roman-figure output, subjective emotion
wording, corpus example IDs for song references, and theory registry IDs. A
failed draft gets one repair attempt, then a deterministic response. F73
exposes this workflow at `POST /v2/ai/query`:

```bash
curl -N -H 'Content-Type: application/json' \
  -d '{"query":"Recommend the next chord after C G Am in C major"}' \
  http://localhost:8000/v2/ai/query
```

The response is SSE with `step`, `partial`, `final`, and `error` events.
`partial` text is emitted only after grounding validation. The API permits
20 assistant queries per IP per UTC hour and uses
`HCG_DAILY_AI_BUDGET_USD` (default $2.00) to cap daily model spend from
logged usage. It temporarily reserves a conservative upper bound for each
in-flight query, so requests near the cap may receive 429 before the logged
total reaches it. Oversized model prompts fall back to deterministic output.
The private `hcg.ai_query_logs` table records outcomes and
estimated model cost; `hcg.rate_limits` holds hourly counters. Apply migration
`0011_ai_query.sql` before enabling the endpoint. Set a private
`HCG_IP_HASH_SECRET` in the API deployment; production requests are rejected
without it. The deterministic endpoints are available when the assistant
returns 429.

The `/assistant` page reads this SSE stream through the same-origin API proxy.
It shows the workflow steps, grounded explanation and cited facts, and
playable progression options with links to the explorer and generator.
The simple/technical switch reveals theory labels and citation IDs.
When the assistant reaches its rate or budget limit, the page links back to
the deterministic workbench.

For a one-word song title that is also an ordinary word, use explicit song
wording (for example, “the song Yesterday”) so the validator can require a
matching `example:*` row. A bare sentence such as “Yesterday is in C” is
ambiguous without that context.

The 30-case F72 adversarial corpus is in
`backend/tests/eval/ai_adversarial.jsonl`. Unit tests cover the validator rules
and check the corpus structure. A separate real-model evaluation runner is
available for optional experiments.

## Phase Direction

Phase 2 will add harmonic color profiles, embeddings,
pgvector similarity search, intent-conditioned
recommendations, graph exploration, and playback.

Phase 3 will add a retrieval-grounded LLM/agent layer that
uses validated internal tools instead of inventing musical
claims from model memory.
