# Live AI repair verification — 2026-09-30

[Run 36800279216](https://github.com/siddsan7/HarmonicColorGraph/actions/runs/36800279216), commit 7d495d7, completed 40/40 live Anthropic cases with seeded services at $2.467141. Parsing, routing, tool correctness, theory validity, required tags, fact coverage, schema and forbidden-claim checks all scored 1.0. Intent/color match remained 8/12 (0.6667), below 0.75, so acceptance failed.

This isolated the remaining failure to deterministic color/ranking behavior rather than parser direction or comparison routing. A subsequent signed-brightness normalization correction in 5fe998b preserves differences between negative brightness values. Frozen local checks now pass 9/12 directional cases with supplied expected intent axes; that is a diagnostic, not a live model pass. A live recheck is pending.

Some explanations still fall back after provider structured-output validation. Claim-validation failures now expose stable rule codes and deterministic explain-route fallbacks retain analyzer citations. These fallbacks remain labeled and must not be described as generated-prose success. Some seeded explain-transition requests also report corpus_unavailable. [Full report](ai-live-repair-2026-09-30.json).
