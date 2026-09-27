# Harmonic Color Graph

This is the Git root. The app is in `harmonic-color-graph/` (Next.js, FastAPI,
Postgres, Redis). Preserve its npm lockfile and existing Python setup.

On this Windows host, the ignored `AGENTS.override.md` is the current resume
packet. It replaces this file when present. If absent, run
`python scripts/resume.py status` and `python scripts/resume.py verify` before
choosing work. If the local record is missing, ask which workstream to resume.
Never infer the next feature from the historical plan alone.

Only read references that bear on the chosen change. Keep harmonic analysis,
scoring, and validation deterministic. Do not run a corpus reload incidentally.
Implement and verify authorized work, then checkpoint the record at a working
slice, blocker, PR, or merge. A merge or deployment requires user or assigned
reviewer review and required gates.
