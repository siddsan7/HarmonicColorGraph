"""Shared per-section aggregation context derivation (F22: aggregate,
ngrams, patterns all group by the same context set).
"""

from __future__ import annotations

# A context is dropped (except `global`, which is always kept) when it has
# fewer than this many observations. feature-specs/v2-implementation-plan.md
# F20 names this threshold for `aggregate`'s TRANSITIONS_TO; ngrams/patterns
# reuse it so "contexts worth modeling" means the same thing everywhere.
MIN_CONTEXT_OBSERVATIONS = 2000


def context_keys(genre: str | None, section: str | None, decade: str | None) -> list[str]:
    contexts = ["global"]
    if genre:
        contexts.append(f"genre:{genre}")
    if section:
        contexts.append(f"section:{section}")
    if decade:
        contexts.append(f"decade:{decade}")
    if genre and section:
        contexts.append(f"genre_section:{genre}:{section}")
    return contexts
