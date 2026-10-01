# AI assistant evaluation

F76 uses the 40-case [`ai_benchmark.jsonl`](../../backend/tests/eval/ai_benchmark.jsonl) corpus. Each case contains an input, intended route and optional color-axis targets, expected tool set, maximum additional calls, prohibited output patterns, and required theory registry tags. The corpus covers all six workflow routes.

From `backend/`, run `hcg-eval ai --max-cost-usd 5` against `DATABASE_URL`, or add `--fixture` for seeded local data. The live runner requires `ANTHROPIC_API_KEY`. It checks the conservative per-request cost bound before starting each case and stops rather than exceed the cap. A provider failure, missing usage, or malformed token counts reserves the full bound for that case; the report separates metered cost from the upper bound used for admission. It writes `.agent-logs/ai-eval/ai.json` and `ai.md`. The [weekly/manual workflow](../../../.github/workflows/ai-eval.yml) uploads those reports even when a threshold fails. The workflow has no database secret, so it uses the repository's deterministic seeded tool fixture for reproducible graph, similarity, and recommendation evidence. A separate deployment check is needed to assess the production corpus.

The scoring rules are:

| Metric | Rule | Required |
|---|---|---:|
| Schema validity | Final response round-trips through `AssistantResponse` JSON schema | 100% |
| Must-not | No case-specific prohibited regex matches the response | 100% |
| Routing | Final route equals expected route | ≥90% |
| Intent match | Each target axis is within 0.35 of the parsed intent value and the top recommendation's authoritative color delta, using the recommender's axis orientation, moves in the requested direction | ≥75% |
| Intent parse match | Target color axes alone match the structured parser result | Reported |
| Color axis match | Top recommendation's scorer-aligned color delta aligns with the target | Reported |
| Tool correctness | Expected set is called and extra calls stay under the case allowance | 100% |
| Theory validity | All claims pass the grounding validator and candidate facts/tools are traceable | 100% |
| Required theory tags | Case-required relationship IDs occur in claim labels | 100% |
| Fact coverage | Validator-passing claims divided by all claims | ≥95% |

Passing also requires all 40 cases to complete, at least one scored intent case, and at least one claim. The fact-coverage measure is a deterministic faithfulness proxy; it does not prove semantic entailment. The score report includes per-case tool calls, validator codes, model usage, and estimated API cost. No prompt or model response text is persisted in the report.

Color matching reads the top `recommend_next` result's `color` deltas and uses the recommender's `intent_score` orientation. Surprise uses 0.5 as a neutral point because its native delta is in `[0, 1]`: below 0.5 meets a common request, above 0.5 meets a surprising request. A missing color delta fails that case.

## Local baseline (2026-09-27)

The offline seeded fixture completed 40/40 cases with schema validity 100%, must-not 100%, routing 92.5%, tool correctness 92.5%, and theory validity 100%. Intent match and fact coverage were 0% because the fallback has no model-parsed axes or generated claims (0 claims). This baseline **fails** the live acceptance thresholds and is a diagnostic of the harness only. The live workflow will generate the dated result artifact once its secret is configured.

`hcg-eval ai --offline --fixture` runs the deterministic fallback for diagnostics without a model. Its intent and claim coverage scores are expected to be low and must not be presented as live-model acceptance. As of this commit, live Claude results and the F76 thresholds are **unverified** because `ANTHROPIC_API_KEY` has not been configured in this environment.

If `ragas` and `anthropic` are installed, `--ragas` adds a separately billed [Ragas faithfulness](https://docs.ragas.io/en/latest/concepts/metrics/available_metrics/faithfulness/) judge for at most three bounded claim-bearing samples. It is excluded from the weekly workflow and its cost is not included in the main `$5` cap. The deterministic fact-coverage threshold remains authoritative.

The production SSE endpoint retains its request reservation after model failures, workflow errors, client disconnection, or missing/malformed provider usage. Audit `cost_usd` is conservative budget accounting in these cases, not a confirmed provider charge; known successful requests use observed token cost. Token counts must include nonnegative integer input and output counts.
