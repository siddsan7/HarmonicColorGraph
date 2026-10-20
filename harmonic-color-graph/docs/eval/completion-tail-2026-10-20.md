# Completion p95 evidence guard

The proposed production target is completion p95 below 20 seconds per expected route. No reliable production baseline exists for this slice. The unchanged assistant benchmark keeps its existing rubric and gates.

Classic methods considered:

- Deadline reduction: rejected as a speed claim. The 55-second SSE deadline runs between synchronous workflow events and cannot cancel a blocked provider call safely. Shorter timeouts can increase failures.
- Retry bounds: intent and explanation clients already use zero retries, with 8-second and 20-second provider timeouts.
- Query bounds and batching: existing request/tool bounds remain. Feature batching is handled by the completion-median worker.
- Caching: requires complete corpus/model/context identity and stale-data handling. No measured cache opportunity supports a change here.
- Cold starts and region placement: require real deployment measurements before intervention.

Implemented: `tests/eval/tail_acceptance.py` adds failure-aware, per-route acceptance evidence alongside existing descriptive percentiles. Every attempted request remains in the denominator. Failures, disconnects, missing final delivery, missing/invalid times and completions at or above 20 seconds are noncompliant. The source must be explicitly `production_http_sse`; offline, seeded live, and in-process live workflow measurements cannot establish the production target. Production records require HTTP-start-to-final-SSE timing and an explicit final-delivered marker. Current evaluator data cannot provide these and therefore fails closed.

A route needs at least 59 independent representative attempts and a one-sided 95% exact binomial lower confidence bound of at least 95% compliance. With zero failures, 59 observations are the minimum: the lower bound is `0.05 ** (1/59)`. This is an evidence guard, not a guarantee about traffic shifts or correlated samples. The operator must verify representative independent sampling; warm-cache-only or single-instance data do not prove cold-start or multi-region behavior. An isolated failure can pass only when the larger sample still supports the required lower bound.

Focused tests cover the exact all-success bound, 58/59 threshold, failure denominators, invalid and censored outcomes, strict target boundary and source classification. This change does not claim a latency improvement, alter production timeouts, make paid calls or change original benchmark gates.
