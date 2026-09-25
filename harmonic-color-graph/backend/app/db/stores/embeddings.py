"""Version-scoped, bounded pgvector and similarity candidate reads."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.stores.graph import _ActiveStore

SUBJECT_TYPES = {"function", "pattern"}
MODELS = {"chord2vec", "fastrp"}


class EmbeddingStore(_ActiveStore):
    def __init__(self, session: Session):
        super().__init__(session)

    def default_model(self) -> str:
        row = self._one(
            "select manifest->'params'->>'embedding_default_model' as model "
            "from hcg.corpus_versions where version = hcg.v()"
        )
        if not row or row["model"] not in MODELS:
            raise LookupError("Active corpus has no embedding model")
        return row["model"]

    def vector(self, subject_type: str, subject_id: str, *, model: str) -> list[float] | None:
        self._validate(subject_type, model)
        row = self._one(
            """select vec::text as vec from hcg.embeddings
               where version = hcg.v() and subject_type = :kind
                 and subject_id = :subject and model = :model""",
            kind=subject_type,
            subject=subject_id,
            model=model,
        )
        return _parse_vec(row["vec"]) if row else None

    def neighbors(
        self, subject_type: str, subject_id: str, *, model: str, limit: int
    ) -> list[dict]:
        self._validate(subject_type, model, limit)
        vector = self.vector(subject_type, subject_id, model=model)
        if vector is None:
            return []
        return self.neighbors_by_vector(
            subject_type, vector, model=model, limit=limit, exclude=subject_id
        )

    def neighbors_by_vector(
        self,
        subject_type: str,
        vector: list[float],
        *,
        model: str,
        limit: int,
        exclude: str = "",
    ) -> list[dict]:
        self._validate(subject_type, model, limit)
        if len(vector) != 64:
            raise ValueError("Embedding query vector must have 64 values")
        # A literal subject_type keeps the partial HNSW index eligible.
        query = f"""select subject_id,
                    1 - (vec <=> cast(:vec as extensions.vector)) as similarity
                   from hcg.embeddings
                   where version = hcg.v() and subject_type = '{subject_type}'
                     and model = :model and subject_id <> :exclude
                   order by vec <=> cast(:vec as extensions.vector)
                   limit :limit"""
        return self._all(
            query,
            vec="[" + ",".join(map(str, vector)) + "]",
            model=model,
            exclude=exclude,
            limit=limit,
        )

    def popular_patterns(self, *, limit: int = 500) -> list[dict]:
        if not 1 <= limit <= 1000:
            raise ValueError("Pattern limit must be 1..1000")
        return self._all(
            """select pattern as subject_id, support, context_lifts
               from hcg.patterns where version = hcg.v()
               order by support desc limit :limit""",
            limit=limit,
        )

    def pattern_metadata(self, subject_ids: list[str]) -> dict[str, dict]:
        if not subject_ids:
            return {}
        if len(subject_ids) > 200:
            raise ValueError("At most 200 pattern IDs are allowed")
        rows = self._all(
            """select pattern as subject_id, support, context_lifts
               from hcg.patterns where version = hcg.v() and pattern = any(:ids)""",
            ids=subject_ids,
        )
        return {row["subject_id"]: row for row in rows}

    def pattern_colors(self, subject_ids: list[str], axis: str) -> dict[str, float]:
        if not subject_ids:
            return {}
        rows = self._all(
            """select subject_id, (axes->'raw_normalized'->>:axis)::double precision as value
               from hcg.color_profiles
               where version = hcg.v() and subject_type = 'pattern'
                 and subject_id = any(:ids)""",
            ids=subject_ids,
            axis=axis,
        )
        return {row["subject_id"]: row["value"] for row in rows if row["value"] is not None}

    def chord_candidates(self, chord: str, *, limit: int = 400) -> list[dict]:
        """Use the chord's four strongest functions to bound candidate chords."""
        return self._all(
            """with seed as (
                 select e.dst_key, e.count
                 from hcg.nodes n
                 join hcg.corpus_versions cv on cv.version = n.version
                 join hcg.edges_compact e on e.version_key = cv.version_key
                      and e.src_key = n.node_key and e.type_code = 2
                 where n.version = hcg.v() and n.id = :node
                 order by e.count desc limit 4
               ), candidates as (
                 select distinct e.src_key
                 from seed s join hcg.corpus_versions cv on cv.version = hcg.v()
                 join hcg.edges_compact e on e.version_key = cv.version_key
                      and e.dst_key = s.dst_key and e.type_code = 2
                 limit :limit
               )
               select n.label as chord, f.label as token, e.count
               from candidates c
               join hcg.nodes n on n.node_key = c.src_key and n.version = hcg.v()
               join hcg.corpus_versions cv on cv.version = n.version
               join hcg.edges_compact e on e.version_key = cv.version_key
                    and e.src_key = n.node_key and e.type_code = 2
               join hcg.nodes f on f.node_key = e.dst_key and f.version = n.version""",
            node=f"chord:{chord}",
            limit=limit,
        )

    @staticmethod
    def _validate(subject_type: str, model: str, limit: int = 10) -> None:
        if subject_type not in SUBJECT_TYPES or model not in MODELS:
            raise ValueError("Unsupported embedding subject or model")
        if not 1 <= limit <= 200:
            raise ValueError("Embedding neighbor limit must be 1..200")


def _parse_vec(value: str) -> list[float]:
    return [float(item) for item in value.strip("[]").split(",")]
