# Assistant terminal-event handling - 2026-10-01

The browser client kept reading after a valid final SSE event. A transport that
remained open left the request pending; a later connection error rejected an
already delivered answer. Two deterministic regression tests reproduced both
failures before the fix. The client now returns on the final frame and cancels
the reader, while transport failures before that frame still reject normally.

Four parser tests, the complete frontend lint/typecheck/unit/build checks, and
eight mocked Assistant browser tests pass. The latter cover all six routes,
rate and stream errors, and accessibility. These tests spend no model credits.

The [production run](ai-production-pr67-2026-10-01.json) stopped after two
requests on `bd42171`. The first completed over HTTP. The second received HTTP200
and a query ID before RemoteProtocolError; its exact database audit records a
final response, no error category, and complete model usage costing $0.031876.
The first cost $0.024901, giving $4.709505 cumulative task spending with no
unresolved cost reservation. The original unknown-outcome ledger is preserved.
The second HTTP delivery remains unverified and the run remains halted. Runtime
logs could not be retrieved because the provider returned ExceedsBillingLimitError.
The client bug is not established as the cause of this interruption.

The private evaluation driver also now stops at a received final event, persists
its timestamp/hash, and still requires the exact durable audit response and
cost to match. Its new trailing-error regression failed before and passes after;
all ten budget/resume tests pass. No failed paid request was replayed. The
production daily cap was restored to $2 and redeployed on the same revision.
