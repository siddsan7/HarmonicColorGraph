# Native-schema live fixture evaluation - 2026-10-01

CI run 36840188769, attempt 1, revision `bd4217149cc8ef326b8965d13ef033f11e697e69`.
All 40 live seeded-fixture cases passed configured thresholds. Intent was 10/12
(83.33%); schema, routing, must-not, tool, theory, tags and fact coverage were 100%.
See the [complete report](ai-live-native-pr67-2026-10-01.json).

Accounted and metered cost were $1.396511 with no unknown-cost cases.
Cumulative authorized task spending is $4.652728 of $10; the full $5 temporary
reservation was reconciled from the verified workflow artifact.

Native schema generation eliminated the claims-container parsing errors seen
in PR66. Fallbacks decreased from 31 to 9: seven provenance-validation fallbacks
and two clarification cases. The deterministic validators remain unchanged.
One fixture explanation reported corpus_unavailable. Passing thresholds does
not mean every generated explanation was accepted, and fixture results do not
establish production acceptance. This report does not contain latency data.
