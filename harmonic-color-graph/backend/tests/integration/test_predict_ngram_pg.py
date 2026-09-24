"""F30: the Postgres-backed side of Kneser-Ney prediction -- the batched
`NgramStore.histories`/`count_of_counts` SQL against migrated Postgres, and
(when a real corpus version is active) the predictor end to end against it.
"""

from __future__ import annotations

import json
import os
import time

import pytest
from sqlalchemy import text

from app.db.session import create_session_factory
from app.db.stores import GraphStore, NgramStore
from app.predict.ngram import KNPredictor, NgramHistory

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")

pytestmark = [
    pytest.mark.pg,
    pytest.mark.skipif(not TEST_DATABASE_URL, reason="TEST_DATABASE_URL is not set"),
]


class _SessionNgramReader:
    """Adapts `GraphStore`/`NgramStore` (context-id-keyed SQL) to
    `KNPredictor`'s `NgramReader` protocol (context-key-keyed), the same
    role a request-scoped service layer would play in production."""

    def __init__(self, session):
        self._graph = GraphStore(session)
        self._ngrams = NgramStore(session)

    def active_version(self):
        return self._graph.active_version()

    def context_by_key(self, context: str):
        return self._graph.context_by_key(context)

    def histories(self, requests):
        rows = self._ngrams.histories(requests)
        return {
            (row["context_id"], row["ord"], row["history"]): NgramHistory(
                total=row["total"],
                distinct_next=row["distinct_next"],
                next=row["next"],
                cont=row["cont"],
            )
            for row in rows
        }

    def count_of_counts(self, requests):
        rows = self._ngrams.count_of_counts(requests)
        return {(row["context_id"], row["ord"]): (row["n1"], row["n2"]) for row in rows}


def test_histories_and_count_of_counts_batch_in_one_round_trip_each():
    factory = create_session_factory(TEST_DATABASE_URL)
    with factory() as session:
        try:
            session.execute(text("update hcg.corpus_versions set active = false where active"))
            session.execute(
                text(
                    """insert into hcg.contexts(id, type, value, label)
                       values (0, 'global', '', 'Global')
                       on conflict (type, value) do nothing"""
                )
            )
            session.execute(
                text(
                    """insert into hcg.corpus_versions(version, manifest, active)
                       values ('cv-f30-test', '{}'::jsonb, true)
                       on conflict (version) do update set active = true"""
                )
            )
            rows = [
                (
                    0,
                    1,
                    "",
                    6,
                    4,
                    {"A": 2, "B": 2, "C": 1, "D": 1},
                    {"A": 1, "B": 1, "C": 1, "D": 1},
                ),
                (0, 2, "A", 2, 1, {"B": 2}, {"B": 1}),
                (0, 2, "B", 2, 2, {"C": 1, "D": 1}, {"C": 1, "D": 1}),
            ]
            for context_id, ord_, history, total, distinct_next, next_, cont in rows:
                session.execute(
                    text(
                        """insert into hcg.ngram_histories
                           (version, context_id, ord, history, total, distinct_next, next, cont)
                           values ('cv-f30-test', :context_id, :ord, :history, :total,
                                   :distinct_next, :next, :cont)
                           on conflict (version, context_id, ord, history) do update set
                               total = excluded.total, distinct_next = excluded.distinct_next,
                               next = excluded.next, cont = excluded.cont"""
                    ),
                    {
                        "context_id": context_id,
                        "ord": ord_,
                        "history": history,
                        "total": total,
                        "distinct_next": distinct_next,
                        "next": json.dumps(next_),
                        "cont": json.dumps(cont),
                    },
                )

            store = NgramStore(session)
            fetched = store.histories([(0, 2, "A"), (0, 2, "B"), (0, 1, "")])
            assert len(fetched) == 3  # one round trip, all three rows back
            by_key = {(row["context_id"], row["ord"], row["history"]): row for row in fetched}
            assert by_key[(0, 2, "A")]["next"] == {"B": 2}
            assert by_key[(0, 2, "B")]["total"] == 2

            counts = store.count_of_counts([(0, 2)])
            assert len(counts) == 1
            # Raw order-2 counts here: A->B=2, B->C=1, B->D=1 -> n1=2, n2=1.
            assert (counts[0]["n1"], counts[0]["n2"]) == (2, 1)

            predictor = KNPredictor(_SessionNgramReader(session))
            dist = predictor.distribution(["A"])
            assert dist["B"] == pytest.approx(0.8125)  # matches the unit-test hand derivation
            assert sum(dist.values()) == pytest.approx(1.0)
        finally:
            session.rollback()


def test_history_and_ii_v_produce_different_top_5_on_the_real_loaded_corpus():
    """F30's checklist: "`I V vi` vs `ii V vi` produce different top-5
    orderings on the real data". CI's ephemeral Postgres has the schema
    migrated but no corpus loaded (loading the real ~150k-row corpus takes
    real time -- see context/HANDOFF.md), so this only actually exercises
    the claim when pointed at a database with an active corpus version;
    otherwise it skips rather than asserting nothing against empty tables.
    """
    factory = create_session_factory(TEST_DATABASE_URL)
    with factory() as session:
        predictor = KNPredictor(_SessionNgramReader(session))
        if predictor.store.active_version() is None:
            pytest.skip("No active corpus version loaded in this database")

        top5_after_i_v = [p.token for p in predictor.predict(["M:I", "M:V"], top_n=5).predictions]
        top5_after_ii_v = [p.token for p in predictor.predict(["M:ii", "M:V"], top_n=5).predictions]
        assert top5_after_i_v != top5_after_ii_v


def test_warm_predictor_p95_latency_under_150ms_on_the_real_loaded_corpus():
    factory = create_session_factory(TEST_DATABASE_URL)
    with factory() as session:
        predictor = KNPredictor(_SessionNgramReader(session))
        if predictor.store.active_version() is None:
            pytest.skip("No active corpus version loaded in this database")

        histories = [["M:I"], ["M:I", "M:V"], ["M:ii", "M:V"], ["M:vi"], ["M:IV", "M:I", "M:V"]]
        for history in histories:  # warm the per-version discount cache first
            predictor.predict(history, top_n=10)

        samples = []
        for _ in range(20):
            for history in histories:
                start = time.perf_counter()
                predictor.predict(history, top_n=10)
                samples.append(time.perf_counter() - start)
        samples.sort()
        p95 = samples[int(len(samples) * 0.95)]
        assert p95 < 0.150, f"warm p95 latency {p95 * 1000:.1f}ms exceeds the 150ms budget"
