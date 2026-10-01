# Contextual recommendation and explanation corrections

The production baseline on `247b025` stopped failed/incomplete after 24 of 40
cases. All twelve intent cases had completed, with eight passing; twelve
responses used labeled explanation fallbacks. Actual spend was $1.258135.
No further baseline requests were sent. Production daily budget was restored
to $2 in READY deployment `dpl_CsPepmCbPPSgHziZSmvWuQnbxT9f`, on the same
commit. The [partial report](ai-production-baseline-2026-10-01.json) is not a
full acceptance pass.

Two independent development regressions reproduced general defects:

- A 0.1 slider had the same influence as a 1.0 slider. Intent normalization now
  preserves weak magnitudes and bounds combined strong axes.
- In D major, A7 → D → G incorrectly reported zero resolution change for the
  departure from D. Feature extraction now compares adjacent arrivals using
  available history. Smoothness deltas compare both transitions, while
  `vl_cost` remains the absolute incoming voice-leading cost. A one-chord
  history retains the existing zero baseline for unavailable prior motion.

These are soft ranking preferences. A requested direction can be unattainable;
labels now say “Intent ranked” rather than asserting a match. Subtracting a
shared historical baseline generally does not change candidate ordering.

Explanation prompts now omit duplicate analysis and repeated perceptual prose,
while preserving numeric values, confidence, source, musical identities, key
regions, relationships, and citations. Public tool results and validators retain
the full evidence. Structured parsing failures distinguish output-token limits
from other parse errors without exposing provider content; usage is recorded
before parsing failure. Oversized prompts skip futile repair calls. Token,
request, and spending limits are unchanged. The historical generic errors do
not establish which failure cause occurred in production.

Verification: both defect regressions failed before their respective fixes;
focused workflow/recommendation/color checks passed, including provider-failure
usage accounting and prompt evidence preservation. Full backend non-Postgres
suite passed (118.906 seconds); lint passed. Initial format check failed on
mixed line endings; formatter and subsequent lint/format checks passed.
Independent reviewer ran 40 focused checks successfully. Real Postgres and
Docker checks remain required in PR CI.

[Frozen development/test recheck](hybrid-context-recheck-2026-10-01.json):
400 positions per split, seeds 54/53, zero song overlap, unchanged weights and
selection diversity. All gates pass. Test MRR is 0.6832 versus baseline 0.6927;
coverage 87 versus 80; intent results are 27/27/30/28 of 30. No benchmark cases,
thresholds, or fitted weights were modified. A fresh production AI run remains
pending reviewed release and must include the prior $1.258135 in the $10 cap.


## Follow-up after PR65 production evaluation

PR65 passed all five CI gates in run36835420807 and exact-head review, then
merged as `540c4e7`. Its production evaluation stopped at15/40 after all12
intent cases finished8/12. New spend was $0.576628; cumulative task spend is
$1.834763. The [second partial report](ai-production-pr65-2026-10-01.json)
remains failed/incomplete. The daily cap is restored2 in READY deployment
`dpl_3eWm6foXTJyHYS4ooh2JB7YbD2Yz` on the same commit.

The dreamy heuristic describes smooth incoming motion, whereas the explicit
smooth slider requests a change from the prior arrival. Its motion term now
uses1-vl_cost when candidate features exist. A separate D/E-major regression
holds the last chord and candidate fixed while changing the predecessor:
dreamy fit stays constant while contextual smoothness delta changes. This
failed before the correction and passes afterward. No frozen cases or
thresholds changed.

Structured errors now include only allowlisted Pydantic schema fields and
error types (at most four codes), never messages, inputs, context, raw model
arguments, or unknown field names. Missing structured output and generic tool
parse failures have distinct fixed codes. The prompt explicitly restates the
existing500-character claim and nonempty citation constraints. Real installed
parser tests reproduce missing/empty citations, overlong text, malformed
claims, unknown fields/tool names, and missing tool calls without paid calls.
The observed production structured_parse errors alone do not prove which
schema violation occurred.

Full backend checks passed (95.563-second non-Postgres suite), followed by
focused parser regression and lint/format checks after the review correction
from invalid_tool_arguments to the accurate generic tool_parse code. A single
CI fixture evaluation is proposed after reviewed release; its full $5 cap
must be reserved before dispatch and reconciled from the final cost artifact.
It will not substitute for production acceptance.
