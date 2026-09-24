"""F23 graph migration and active-version reads against migrated Postgres."""

import os

import pytest
from sqlalchemy import text

from app.db.session import create_session_factory
from app.db.stores import FactStore, GraphStore, NgramStore, PatternStore

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")

pytestmark = [
    pytest.mark.pg,
    pytest.mark.skipif(not TEST_DATABASE_URL, reason="TEST_DATABASE_URL is not set"),
]


def test_graph_schema_has_rls_and_active_version_view():
    factory = create_session_factory(TEST_DATABASE_URL)
    with factory() as session:
        rls = dict(
            session.execute(
                text(
                    """select relname, relrowsecurity from pg_class
                       join pg_namespace on pg_namespace.oid = pg_class.relnamespace
                       where nspname = 'hcg' and relkind = 'r'"""
                )
            ).all()
        )
        assert {
            "corpus_versions",
            "contexts",
            "nodes",
            "edges",
            "ngram_histories",
            "patterns",
            "pattern_examples",
            "transition_examples",
            "song_refs",
            "relationship_types",
            "facts",
        }.issubset(rls)
        assert all(rls[name] for name in rls)
        assert (
            session.execute(text("select hcg.v()")).scalar_one()
            == session.execute(text("select version from hcg.active_version")).scalar_one_or_none()
        )


def test_stores_only_read_active_version_after_atomic_flip():
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
            for version, count in (("cv-f23-test-a", 10), ("cv-f23-test-b", 20)):
                session.execute(
                    text(
                        """insert into hcg.corpus_versions(version, manifest, active)
                           values (:version, '{}'::jsonb, false)"""
                    ),
                    {"version": version},
                )
                for node_id in ("function:M:V", "function:M:I"):
                    session.execute(
                        text(
                            """insert into hcg.nodes(version, id, type, label)
                               values (:version, :node_id, 'function', :node_id)"""
                        ),
                        {"version": version, "node_id": node_id},
                    )
                session.execute(
                    text(
                        """insert into hcg.edges(version, src, dst, type, context_id, count, prob)
                           values (:version, 'function:M:V', 'function:M:I',
                                   'TRANSITIONS_TO', 0,
                                   :count, 0.5)"""
                    ),
                    {"version": version, "count": count},
                )
                session.execute(
                    text(
                        """insert into hcg.ngram_histories
                           (version, context_id, ord, history, total, distinct_next, next, cont)
                           values (:version, 0, 2, 'M:V', :count, 1,
                                   '{"M:I": 1}'::jsonb, '{}'::jsonb)"""
                    ),
                    {"version": version, "count": count},
                )
                session.execute(
                    text(
                        """insert into hcg.patterns
                           (version, pattern, length, support, song_count)
                           values (:version, 'M:I M:V M:I', 3, :count, 1)"""
                    ),
                    {"version": version, "count": count},
                )
                session.execute(
                    text(
                        """insert into hcg.song_refs(version, song_id, genre)
                           values (:version, 'song-f23', 'pop')"""
                    ),
                    {"version": version},
                )
                session.execute(
                    text(
                        """insert into hcg.pattern_examples
                           (version, pattern, song_id, section, ordinal, position, rank)
                           values (:version, 'M:I M:V M:I', 'song-f23', 'chorus', 1, 4, 1)"""
                    ),
                    {"version": version},
                )
                session.execute(
                    text(
                        """insert into hcg.transition_examples
                           (version, from_token, to_token, song_id, section, ordinal,
                            position, rank)
                           values (:version, 'M:V', 'M:I', 'song-f23', 'chorus', 1, 7, 1)"""
                    ),
                    {"version": version},
                )
                session.execute(
                    text(
                        """insert into hcg.facts
                           (version, fact_id, kind, subject, template)
                           values (:version, 'transition:M:V->M:I:global',
                                   'transition', 'M:V->M:I', 'resolves')"""
                    ),
                    {"version": version},
                )
            graph = GraphStore(session)
            ngrams = NgramStore(session)
            patterns = PatternStore(session)
            facts = FactStore(session)
            for version, count in (("cv-f23-test-a", 10), ("cv-f23-test-b", 20)):
                session.execute(text("update hcg.corpus_versions set active = false where active"))
                session.execute(
                    text("update hcg.corpus_versions set active = true where version = :version"),
                    {"version": version},
                )
                assert graph.active_version() == version
                assert graph.node("function:M:I")["version"] == version
                assert graph.outgoing_edges("function:M:V")[0]["count"] == count
                assert graph.incoming_edges("function:M:I")[0]["count"] == count
                assert graph.context_by_key("global")["id"] == 0
                assert graph.function_adjacency(0)[0]["count"] == count
                assert graph.edges_between("function:M:V", "function:M:I")[0]["count"] == count
                assert ngrams.history(0, 2, "M:V")["total"] == count
                assert patterns.pattern("M:I M:V M:I")["support"] == count
                assert patterns.examples("M:I M:V M:I")[0]["genre"] == "pop"
                assert patterns.examples("M:I M:V M:I")[0]["position"] == 4
                assert patterns.transition_examples("M:V", "M:I")[0]["song_id"] == "song-f23"
                assert patterns.transition_examples("M:V", "M:I")[0]["position"] == 7
                assert facts.fact("transition:M:V->M:I:global")["version"] == version
                assert facts.by_subject("M:V->M:I")[0]["version"] == version
                assert graph.node("missing") is None
        finally:
            session.rollback()
