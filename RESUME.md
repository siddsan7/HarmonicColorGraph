# HCG local continuation

The ignored root `AGENTS.override.md` shows the one active workstream. Its
source is `<git-common-dir>/agent-workbench/resume.json`, shared by local Git
worktrees on this host. The root `AGENTS.md` is a fallback for a new clone.
The old app `context/HANDOFF.md` is historical product context, not the task
selector.

From any local worktree root:

```powershell
python scripts/resume.py status
python scripts/resume.py verify
```

Older worktree branches might not yet contain `scripts/resume.py`. On this
host, run the portable copy with `--repo .`:

```powershell
python C:/Users/sidds/Documents/Codex/agent-workbench/tools/resume.py verify --repo .
```

At a feature start, after a working slice, when blocked, before handoff, and
after a PR/merge, the primary agent prepares a JSON payload with `task`,
`slice`, `owner` (path, branch, PR), `last_completed` (outcome, revision,
evidence), `next_action`, `acceptance`, `references` (path and read condition),
`verification` (passed, failed, skipped, unverified arrays), `blockers`, and
`stable_rules`. Keep it outside Git, then run:

```powershell
python scripts/resume.py checkpoint --input PATH_TO_PAYLOAD --expect CURRENT_REVISION
```

The owner worktree, branch, HEAD and diff must match the previous checkpoint.
If they do not, inspect the work and reconcile the record with `--reconcile`.
Changing owners requires `--transfer`. Two concurrent writers cannot both
update the same revision. `verify` fails if a mirror is stale; `sync` refreshes
the ignored mirrors after the authoritative record is known to be correct.

This local record is not carried to another machine by Git. A fresh clone must
choose the active workstream explicitly before initializing its own record.
