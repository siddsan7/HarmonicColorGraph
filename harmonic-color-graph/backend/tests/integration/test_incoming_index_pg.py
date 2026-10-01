"""Incoming index plan changes must preserve bounded candidates and versions."""

import os

import pytest
from sqlalchemy import text

from app.db.session import create_session_factory
from app.db.stores.embeddings import EmbeddingStore
from app.db.stores.graph import GraphStore

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")
pytestmark = [
    pytest.mark.pg,
    pytest.mark.skipif(not TEST_DATABASE_URL, reason="TEST_DATABASE_URL is not set"),
]


def test_incoming_and_limited_chord_candidates_are_deterministic_and_version_scoped():
    factory = create_session_factory(TEST_DATABASE_URL)
    with factory() as session:
        try:
            session.execute(text("update hcg.corpus_versions set active=false where active"))
            session.execute(
                text(
                    "insert into hcg.contexts(id,type,value,label) values(0,'global','','Global') "
                    "on conflict(type,value) do nothing"
                )
            )
            for version, active in (("cv-index-active", True), ("cv-index-old", False)):
                session.execute(
                    text(
                        "insert into hcg.corpus_versions(version,manifest,active) "
                        "values(:version,'{}',:active)"
                    ),
                    {"version": version, "active": active},
                )
                for node, kind in [(f"function:F{i}", "function") for i in range(5)] + [
                    (f"chord:C{i}", "chord") for i in range(7)
                ]:
                    session.execute(
                        text(
                            "insert into hcg.nodes(version,id,type,label) "
                            "values(:version,:node,:kind,:label)"
                        ),
                        {
                            "version": version,
                            "node": node,
                            "kind": kind,
                            "label": node.split(":")[1],
                        },
                    )
                session.execute(
                    text(
                        "insert into hcg.edges_compact(version_key,src_key,dst_key,"
                        "type_code,context_id,count) "
                        "select cv.version_key,s.node_key,d.node_key,2,0,10 "
                        "from hcg.corpus_versions cv "
                        "join hcg.nodes s on s.version=cv.version and s.type='chord' "
                        "join hcg.nodes d on d.version=cv.version and d.type='function' "
                        "where cv.version=:version and (s.label='C0' or "
                        "(s.label<>'C6' and d.label='F0') or (s.label='C6' and d.label='F4'))"
                    ),
                    {"version": version},
                )
            results = []
            for index_scans in ("off", "on"):
                session.execute(text(f"set local enable_indexscan={index_scans}"))
                session.execute(text(f"set local enable_bitmapscan={index_scans}"))
                rows = EmbeddingStore(session).chord_candidates("C0", limit=3)
                assert sorted({row["chord"] for row in rows}) == ["C0", "C1", "C2"]
                results.append(rows)
                incoming = GraphStore(session).incoming_edges("function:F0")
                assert len(incoming) == 6
                assert {row["version"] for row in incoming} == {"cv-index-active"}
            assert results[0] == results[1]
            all_candidates = EmbeddingStore(session).chord_candidates("C0")
            assert "C6" not in {row["chord"] for row in all_candidates}
        finally:
            session.rollback()
