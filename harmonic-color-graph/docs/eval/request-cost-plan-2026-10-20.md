# Cost per completed assistant request

## Goal and evidence

Reduce total API cost per completed request without lowering completion or measured
response quality. There is no comparable live baseline for this change. No paid
evaluations, model changes, token rates or budget limits are authorized by this slice.

The current evaluator includes failed attempts in its accounted-cost numerator.
`UsageMeter.cost_usd` estimates API cost from returned token usage and configured
rates. It also adds conservative charges when usage is missing. The evaluator can
reserve the entire bounded request cost after an uncertain failure. Neither total
is an invoice or an unconditional measure of provider-reported usage cost.

## Classic methods assessed against this implementation

| Method | Case-specific assessment | Plan |
| --- | --- | --- |
| Reduce repeated model calls and repairs | Repair can add a second main-model call; wave 1 already adds grounded repair improvements. | Measure all model attempts, including failed attempts, before claiming savings. |
| Shorten prompts and outputs | Compact prompts are already in PR 78. UTF-8 bytes alone cannot prove token or dollar savings. | Use actual returned usage and unchanged quality checks in a paired live run when authorized. |
| Cache repeated work or model responses | Tools have deterministic work that can be reused; prompt and response caching depend on repeated context and provider conditions. | Record comparable cache conditions. Do not assume a cache hit or introduce response caching without invalidation and quality checks. |
| Select a smaller model | The workflow already separates fast intent and main explanation models. | Defer model changes until comparable live quality, failure and cost evidence is authorized. |
| Reduce conservative reservations | Reservations protect the cap after uncertain usage. Lowering a reservation does not lower API cost. | Keep all caps and reservation logic intact; report the difference separately. |

## Implemented evidence guard

`tests/eval/ai_cost_diagnostics.py` reports route-specific attempted and completed
requests, failed attempts, metered estimates, accounted cost and reservation excess.
Both cost-per-completed denominators exclude failed completions while their
numerators retain all attempted cost. No completed requests produces `null`, not
zero. Reported-usage estimates are unavailable when any attempt has incomplete
usage evidence. Missing completeness markers fail closed.

The paired comparator requires live mode, matching case IDs and expected routes,
the same completion pattern, complete usage, and unchanged per-case benchmark
quality flags including fallback. Explicit comparison identities must document
models, corpus, pricing, input cases, rubric, context and cache conditions.
Prompt source identities must be recorded on both sides but may differ. An
optimization can change its implementation while preserving the evaluation context.
The comparator rejects zero-cost baselines and duplicate case IDs. A favorable
comparison means an observed estimated-cost reduction; it does not establish
statistical significance, invoice savings or production readiness by itself.

The runner records `cost_usage_complete` on each case from
`not uncertain_cost and meter.unknown_usage_calls == unknown_before`, and includes
`cost_diagnostics(rows)` in the report. The quality comparison also preserves
claim counts and validated claim counts. Do not fabricate comparison identities:
populate them from the actual run configuration before using the optional paired
comparator. Existing `cost_per_completed_request_usd` retains its historical
accounted-cost meaning for compatibility.

## Validation and limits

Seventeen deterministic helper tests pass. They cover failed-attempt spend,
reservation separation, zero completions, unknown usage, offline runs, changed
quality or completion, mismatched routes and cases, missing source identities,
duplicate IDs, and invalid money values. Ruff lint and formatting pass.

No live run was made. These tests establish accounting and comparison behavior;
they do not show that requests became cheaper. Subjective musical quality and
other latency and ranking release gates remain separate requirements.
