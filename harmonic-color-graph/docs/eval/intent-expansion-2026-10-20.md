# Explicit fallback language recovery — October 20, 2026

This local correction recovers two explicit phrases during model outages. It recognizes
`tenser` as the comparative of tense, and treats `a little bit` as the same weak
strength (0.3) as `a little`. Previously the former was omitted and the latter
silently received the ordinary 0.7 strength. Valid model output still takes precedence.
No generator target mapping, ranking weights, candidate pool, original assistant
benchmark or musical rubric changed.

## Methods and applicability

Classic methods include prompt examples, model replacement, grammar expansion,
ranker tuning and broader candidate retrieval. Parsing already recovers all 12
expected axes in the original offline assistant benchmark. Its three outcome
misses comprise two infeasible fixture pools and one ranking tradeoff. Prompt or
model changes cannot directly repair those deterministic failures. The previous
larger intent-scale experiment failed its quality guards. This slice therefore
fixes independently reproducible explicit-language omissions, and makes no claim
that the original combined intent metric rises above 9/12.

The grammar changes are bounded whole-word recognition and an existing magnitude
synonym. They retain clause-level negation, alternatives, conditionals and axis
conflict abstention. The fallback is still a recovery grammar, not general language
understanding. The synthetic development phrase `less tenser` tests signed modifier
composition; it is not evidence of common natural wording.

## Frozen development and independent validation

The implementation agent wrote 12 development cases and recorded the baseline
before editing grammar. Development sample SHA256:
`2530bcce8b7e15d8f042ac4657f03337bd70951490deaa785cd24525dad76d39`.
[Baseline](intent-expansion-2026-10-20/development-baseline.json) exact dictionaries
were 5/12; [candidate](intent-expansion-2026-10-20/development-candidate.json) was
12/12. These are targeted development regressions, not held-out gains.

The integration agent independently authored and froze 24 language cases before
implementation edits. The implementation agent did not inspect the queries until
the candidate was frozen at commit `a35e8cc823040ed4607211cf777fca314284fe63`,
source SHA256 `b06424136f7148e1348fbf38adaee0c897663a1c38b48ef9cff5caa2c5b8106e`.
The integration agent then evaluated baseline and candidate once each.
[Independent evidence](intent-expansion-2026-10-20/independent-validation.json)
records **24/24 → 24/24**, with zero exact-dictionary regressions. It covers
strength, conflicts, negation, clauses, ordinary directions and controls.
It supports non-regression on that sample, not a held-out quality gain. Published
queries are now regression evidence and must not be described as unseen later.
No grammar tuning followed those results.

## Acceptance and checks

- Passed: focused fallback, expansion, workflow and evaluation unit tests;
  Ruff lint and formatting; existing 30-case parser corpus remains 30/30.
- Passed: explicit unavailable/failed-model recovery and valid-model precedence
  cases, including exact strength preservation.
- Skipped here: full integration/release gates, which the main agent owns.
- Unverified: production combined intent improvement, live provider quality,
  subjective musical usefulness and latency. No paid service was called.

Run from `harmonic-color-graph/backend`:

```powershell
python -m pytest tests/unit/test_ai_workflow.py tests/unit/test_ai_eval.py tests/unit/test_ai_intent_fallback.py tests/unit/test_ai_intent_expansion.py -q
python -m ruff check app/ai/intent_fallback.py tests/unit/test_ai_intent_expansion.py
python -m ruff format --check app/ai/intent_fallback.py tests/unit/test_ai_intent_expansion.py
python -m tests.eval.intent_recovery --output ../.agent-logs/intent-expansion-original.json
```
