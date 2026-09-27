# Observability

FastAPI returns `X-HCG-Trace-Id` and `X-Request-Id` for every HTTP request.
The `http_request` structured log contains the same IDs, route template,
method, and status. Metric events include the trace ID when called inside a
trace. Worker jobs start their own trace with the job ID and type.

Set `OTEL_EXPORTER_OTLP_ENDPOINT` to an OTLP HTTP collector to export spans
and metrics. `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` and
`OTEL_EXPORTER_OTLP_METRICS_ENDPOINT` can override the two derived endpoints.
Use the standard `OTEL_EXPORTER_OTLP_HEADERS` environment variable for collector
credentials. With no endpoint, the API continues to generate trace IDs and
structured metric logs without sending telemetry over the network.
On Vercel, completed requests make a bounded flush of traces and metrics so
short function invocations do not rely on a background export interval.

Spans cover HTTP responses, SQL operations, Redis cache/queue operations,
graph traversal, pgvector neighbors, recommendation retrieval/ranking,
LangGraph nodes, tools, and model calls. SQL spans record only the operation
verb and database type; prompts, request bodies, SQL text and parameters,
cache keys, connection URLs, and credentials are excluded. Model spans include
model name and token counts; AI usage metrics include estimated cost.

Set both `LANGSMITH_API_KEY` and `LANGSMITH_TRACING=true` to trace the
LangGraph workflow in LangSmith. It stays disabled when either is absent.
LangSmith records prompts and tool data for debugging, so configure it only
in an approved workspace. The assistant works when LangSmith is disabled.

API and worker metrics use stable names in `app/core/metrics.py`. Histograms
include `api_latency_ms`, `db_query_latency_ms`, `redis_latency_ms`,
`recommend_retrieval_latency_ms`, `recommend_rerank_latency_ms`,
`ai_llm_latency_ms`, and `job_duration_ms`. Counters include API errors,
database and Redis errors, cache hits/misses, retry and dead-letter jobs,
tool calls, validation failures, repair attempts, fallbacks, tokens, and cost.
`queue_depth` is sampled by the worker every 30 seconds. Worker busy and idle
milliseconds allow utilization to be derived over a time window.
