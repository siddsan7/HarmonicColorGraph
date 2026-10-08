"""Actual graph/vector candidate SQL with isolated, rolled-back corpus fixtures."""

import json
import math
import os

import pytest
from sqlalchemy import text

from app.db.session import create_session_factory
from app.db.stores.recommendation_candidates import CandidateReader

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")
pytestmark = [
    pytest.mark.pg,
    pytest.mark.skipif(not TEST_DATABASE_URL, reason="TEST_DATABASE_URL is not set"),
]


def test_candidate_reads_scope_versions_models_modes_and_previous_similarity():
    factory = create_session_factory(TEST_DATABASE_URL)
    with factory() as session:
        try:
            session.execute(text("update hcg.corpus_versions set active = false where active"))
            session.execute(
                text(
                    "insert into hcg.contexts(id,type,value,label) "
                    "values(0,'global','','Global') "
                    "on conflict(type,value) do nothing"
                )
            )
            context_id = session.execute(
                text("select id from hcg.contexts where type='global' and value=''")
            ).scalar_one()
            for version, active in (("cv-candidate-active", True), ("cv-candidate-old", False)):
                session.execute(
                    text(
                        "insert into hcg.corpus_versions(version,manifest,active) "
                        "values(:version,cast(:manifest as jsonb),:active)"
                    ),
                    {
                        "version": version,
                        "manifest": json.dumps(
                            {"params": {"embedding_default_model": "chord2vec"}}
                        ),
                        "active": active,
                    },
                )
            tokens = {
                "M:I": (1.0, 0.0),
                "M:V": (0.0, 1.0),
                "M:ivmaj7": (0.1, math.sqrt(0.99)),
                "M:IV": (0.6, 0.8),
                "M:ii": (0.8, 0.6),
                "m:i": (0.0, 1.0),
            }
            for token, pair in tokens.items():
                session.execute(
                    text(
                        "insert into hcg.nodes(version,id,type,label) "
                        "values('cv-candidate-active',:id,'function',:token)"
                    ),
                    {"id": "function:" + token, "token": token},
                )
                session.execute(
                    text(
                        "insert into hcg.embeddings(version,subject_type,subject_id,model,vec) "
                        "values('cv-candidate-active','function',:token,'chord2vec',"
                        "cast(:vec as extensions.vector))"
                    ),
                    {"token": token, "vec": json.dumps([*pair, *([0.0] * 62)])},
                )
            for version, model, token in (
                ("cv-candidate-old", "chord2vec", "M:old"),
                ("cv-candidate-active", "fastrp", "M:wrong-model"),
            ):
                session.execute(
                    text(
                        "insert into hcg.embeddings(version,subject_type,subject_id,model,vec) "
                        "values(:version,'function',:token,:model,cast(:vec as extensions.vector))"
                    ),
                    {
                        "version": version,
                        "token": token,
                        "model": model,
                        "vec": json.dumps([0.0, 1.0, *([0.0] * 62)]),
                    },
                )
            for token, probability in (("M:IV", 0.3), ("M:ii", 0.001), ("m:i", 0.5)):
                session.execute(
                    text("""insert into hcg.edges_compact
                    (version_key,src_key,dst_key,type_code,context_id,count,prob,support)
                    select cv.version_key,src.node_key,dst.node_key,1,:context,10,:prob,10
                    from hcg.corpus_versions cv
                    join hcg.nodes src on src.version=cv.version and src.label='M:I'
                    join hcg.nodes dst on dst.version=cv.version and dst.label=:token
                    where cv.version='cv-candidate-active'"""),
                    {"context": context_id, "prob": probability, "token": token},
                )
            for number in range(12):
                session.execute(
                    text(
                        "insert into hcg.embeddings(version,subject_type,subject_id,model,vec) "
                        "values('cv-candidate-active','function',:token,'chord2vec',"
                        "cast(:vec as extensions.vector))"
                    ),
                    {"token": f"M:tie{number:02}", "vec": json.dumps([0.0, 1.0, *([0.0] * 62)])},
                )
            tie_reader = CandidateReader(session)
            _, tied = tie_reader.read(["M:I"], ["M:V"])
            assert [token for token, _ in tied] == [f"M:tie{number:02}" for number in range(10)]
            session.execute(
                text(
                    "delete from hcg.embeddings where version='cv-candidate-active' "
                    "and subject_id like 'M:tie%'"
                )
            )
            reader = CandidateReader(session)
            graph, discoveries = reader.read(["M:I"], ["M:V"])
            assert graph == [("M:IV", pytest.approx(0.3))]
            found = dict(discoveries)
            assert found["M:ivmaj7"] > 0.99
            assert not {"M:old", "M:wrong-model", "m:i"} & found.keys()
            similarities = reader.similarities(
                "M:I", ["M:ivmaj7", "M:IV", "M:V", "M:missing", "m:i"]
            )
            assert similarities == {
                "M:ivmaj7": pytest.approx(0.1),
                "M:IV": pytest.approx(0.6),
                "M:V": pytest.approx(0),
            }
            assert reader.similarities("M:missing", ["M:IV"]) == {}
            session.execute(
                text("update hcg.corpus_versions set manifest='{}'::jsonb where active")
            )
            assert reader.read(["M:I"], ["M:V"]) == (graph, [])
            assert reader.similarities("M:I", ["M:IV"]) == {}
        finally:
            session.rollback()
