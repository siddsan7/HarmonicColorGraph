"""Active-corpus graph reads.

Each statement constrains its version through ``hcg.v()``. A version flip
therefore takes effect on the next statement without a process-local cache;
the loader retains previous versions so in-flight statements can finish.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


class _ActiveStore:
    def __init__(self, session: Session):
        self.session = session

    def active_version(self) -> str | None:
        return self.session.execute(text("select hcg.v()")).scalar_one()

    def _one(self, query: str, **params: Any) -> dict[str, Any] | None:
        row = self.session.execute(text(query), params).mappings().first()
        return dict(row) if row is not None else None

    def _all(self, query: str, **params: Any) -> list[dict[str, Any]]:
        return [dict(row) for row in self.session.execute(text(query), params).mappings()]

    def context(self, context_id: int) -> dict[str, Any] | None:
        return self._one(
            "select id, type, value, label from hcg.contexts where id = :context_id",
            context_id=context_id,
        )

    def context_by_key(self, context: str) -> dict[str, Any] | None:
        context_type, separator, value = context.partition(":")
        if context == "global":
            value = ""
        elif not separator or not value:
            return None
        return self._one(
            """select id, type, value, label from hcg.contexts
               where type = :context_type and value = :value""",
            context_type=context_type,
            value=value,
        )


class GraphStore(_ActiveStore):
    def node(self, node_id: str) -> dict[str, Any] | None:
        return self._one(
            """select id, version, type, label, props
               from hcg.nodes where version = hcg.v() and id = :node_id""",
            node_id=node_id,
        )

    def outgoing_edges(
        self, src: str, *, edge_type: str | None = None, context_id: int | None = None
    ) -> list[dict[str, Any]]:
        filters = []
        params: dict[str, Any] = {"src": src}
        if edge_type is not None:
            filters.append("and type = :edge_type")
            params["edge_type"] = edge_type
        if context_id is not None:
            filters.append("and context_id = :context_id")
            params["context_id"] = context_id
        return self._all(
            f"""select version, src, dst, type, context_id, count, prob, weight, props
               from hcg.edges_read
               where version = hcg.v() and src = :src
               {" ".join(filters)}
               order by type, context_id, dst""",
            **params,
        )

    def incoming_edges(
        self, dst: str, *, edge_type: str | None = None, context_id: int | None = None
    ) -> list[dict[str, Any]]:
        filters = []
        params: dict[str, Any] = {"dst": dst}
        if edge_type is not None:
            filters.append("and type = :edge_type")
            params["edge_type"] = edge_type
        if context_id is not None:
            filters.append("and context_id = :context_id")
            params["context_id"] = context_id
        return self._all(
            f"""select version, src, dst, type, context_id, count, prob, weight, props
               from hcg.edges_read
               where version = hcg.v() and dst = :dst
               {" ".join(filters)}
               order by type, context_id, src""",
            **params,
        )

    def function_adjacency(self, context_id: int) -> list[dict[str, Any]]:
        return self._all(
            """select e.version, e.src, e.dst, e.type, e.context_id,
                      e.count, e.prob, e.weight, e.props
               from hcg.edges_read e
               where e.version = hcg.v() and e.context_id = :context_id
                 and e.type = 'TRANSITIONS_TO'
                 and e.src_type = 'function' and e.dst_type = 'function'
               order by e.src, e.dst""",
            context_id=context_id,
        )

    def edges_between(
        self, src: str, dst: str, *, context_id: int | None = None
    ) -> list[dict[str, Any]]:
        filter_context = "and context_id = :context_id" if context_id is not None else ""
        params: dict[str, Any] = {"src": src, "dst": dst}
        if context_id is not None:
            params["context_id"] = context_id
        return self._all(
            f"""select version, src, dst, type, context_id, count, prob, weight, props
                from hcg.edges_read
                where version = hcg.v() and src = :src and dst = :dst
                  {filter_context}
                order by type, context_id""",
            **params,
        )


class NgramStore(_ActiveStore):
    def history(self, context_id: int, order: int, history: str) -> dict[str, Any] | None:
        return self._one(
            """select version, context_id, ord, history, total, distinct_next, next, cont
               from hcg.ngram_histories
               where version = hcg.v() and context_id = :context_id
                 and ord = :ord and history = :history""",
            context_id=context_id,
            ord=order,
            history=history,
        )

    def histories(self, requests: Sequence[tuple[int, int, str]]) -> list[dict[str, Any]]:
        """F30: fetch every (context_id, order, history) row a single
        prediction request needs -- every order/context in its backoff
        chain -- in one round trip, instead of one query per chain step.
        """
        if not requests:
            return []
        clauses = []
        params: dict[str, Any] = {}
        for index, (context_id, order, history) in enumerate(requests):
            clauses.append(f"(context_id = :c{index} and ord = :o{index} and history = :h{index})")
            params[f"c{index}"] = context_id
            params[f"o{index}"] = order
            params[f"h{index}"] = history
        return self._all(
            f"""select context_id, ord, history, total, distinct_next, next, cont
               from hcg.ngram_histories
               where version = hcg.v() and ({" or ".join(clauses)})""",
            **params,
        )

    def count_of_counts(self, requests: Sequence[tuple[int, int]]) -> list[dict[str, Any]]:
        """F30: per (context_id, order) counts of how many (history, next
        token) pairs have a raw count of exactly 1 or 2, pooled across every
        history at that context and order. Feeds the single-discount
        interpolated Kneser-Ney formula `D = n1 / (n1 + 2*n2)`. Cached by
        the caller (KN discounts change only when the corpus version
        changes, unlike the per-request history fetch above).
        """
        if not requests:
            return []
        clauses = []
        params: dict[str, Any] = {}
        for index, (context_id, order) in enumerate(requests):
            clauses.append(f"(context_id = :c{index} and ord = :o{index})")
            params[f"c{index}"] = context_id
            params[f"o{index}"] = order
        return self._all(
            f"""select context_id, ord,
                      count(*) filter (where raw_count = 1) as n1,
                      count(*) filter (where raw_count = 2) as n2
               from (
                   select h.context_id, h.ord, (kv.value)::int as raw_count
                   from hcg.ngram_histories h, jsonb_each_text(h.next) as kv
                   where h.version = hcg.v() and ({" or ".join(clauses)})
               ) counts
               group by context_id, ord""",
            **params,
        )


class PatternStore(_ActiveStore):
    @staticmethod
    def _example_scope(context: str) -> tuple[str, dict[str, str]]:
        if context == "global":
            return "", {}
        kind, separator, value = context.partition(":")
        if not separator or not value:
            raise ValueError("Invalid evidence context")
        if kind == "genre":
            return "and s.genre = :ctx_genre", {"ctx_genre": value}
        if kind == "section":
            return "and e.section = :ctx_section", {"ctx_section": value}
        if kind == "decade":
            return "and s.decade = :ctx_decade", {"ctx_decade": value}
        if kind == "genre_section":
            genre, separator, section = value.partition(":")
            if separator and genre and section:
                return (
                    "and s.genre = :ctx_genre and e.section = :ctx_section",
                    {"ctx_genre": genre, "ctx_section": section},
                )
        raise ValueError("Invalid evidence context")

    def pattern(self, pattern: str) -> dict[str, Any] | None:
        return self._one(
            """select version, pattern, length, support, song_count,
                      rotations_observed, context_lifts
               from hcg.patterns where version = hcg.v() and pattern = :pattern""",
            pattern=pattern,
        )

    def examples(
        self, pattern: str, *, context: str = "global", limit: int = 5
    ) -> list[dict[str, Any]]:
        scope, params = self._example_scope(context)
        return self._all(
            f"""select e.pattern, e.song_id, e.section, e.ordinal, e.position, e.rank,
                      s.spotify_id, s.genre, s.decade
               from hcg.pattern_examples e
               join hcg.song_refs s on (s.version, s.song_id) = (e.version, e.song_id)
               where e.version = hcg.v() and e.pattern = :pattern
               {scope}
               order by e.rank, e.song_id, e.section, e.ordinal, e.position limit :limit""",
            pattern=pattern,
            limit=limit,
            **params,
        )

    def transition_examples(
        self, from_token: str, to_token: str, *, context: str = "global", limit: int = 5
    ) -> list[dict[str, Any]]:
        scope, params = self._example_scope(context)
        return self._all(
            f"""select e.from_token, e.to_token, e.song_id, e.section, e.ordinal,
                      e.position, e.rank,
                      s.spotify_id, s.genre, s.decade
               from hcg.transition_examples e
               join hcg.song_refs s on (s.version, s.song_id) = (e.version, e.song_id)
               where e.version = hcg.v() and e.from_token = :from_token
                 and e.to_token = :to_token
               {scope}
               order by e.rank, e.song_id, e.section, e.ordinal, e.position limit :limit""",
            from_token=from_token,
            to_token=to_token,
            limit=limit,
            **params,
        )


class FactStore(_ActiveStore):
    def fact(self, fact_id: str) -> dict[str, Any] | None:
        return self._one(
            """select fact_id, version, kind, subject, template, params
               from hcg.facts where version = hcg.v() and fact_id = :fact_id""",
            fact_id=fact_id,
        )

    def by_subject(self, subject: str) -> list[dict[str, Any]]:
        return self._all(
            """select fact_id, version, kind, subject, template, params
               from hcg.facts where version = hcg.v() and subject = :subject
               order by fact_id""",
            subject=subject,
        )
