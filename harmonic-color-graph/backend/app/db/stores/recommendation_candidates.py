"""Bounded active-corpus graph and vector reads for intent recommendations."""

from app.db.stores.embeddings import EmbeddingStore
from app.db.stores.graph import _ActiveStore


class CandidateReader(_ActiveStore):
    def __init__(self, session):
        super().__init__(session)
        self.embeddings = EmbeddingStore(session)
        self.model: str | None = None

    def read(
        self, history: list[str], seeds: list[str]
    ) -> tuple[list[tuple[str, float]], list[tuple[str, float]]]:
        if not history:
            return [], []
        previous = history[-1]
        mode = previous[:2]
        graph = self._all(
            """select dst.label as token, e.prob
               from hcg.nodes src
               join hcg.corpus_versions cv on cv.version = src.version
               join hcg.edges_compact e on e.version_key = cv.version_key
                    and e.src_key = src.node_key and e.type_code = 1
               join hcg.contexts c on c.id = e.context_id and c.type = 'global'
               join hcg.nodes dst on dst.node_key = e.dst_key and dst.version = src.version
               where src.version = hcg.v() and src.id = :source
                 and dst.type = 'function' and left(dst.label, 2) = :mode
                 and e.prob >= 0.005
               order by e.prob desc, dst.label limit 30""",
            source=f"function:{previous}",
            mode=mode,
        )
        try:
            self.model = self.embeddings.default_model()
        except LookupError:
            self.model = None
            return [(row["token"], row["prob"]) for row in graph], []
        # A single bounded lateral query avoids two round trips per seed. The
        # literal subject predicate keeps the partial HNSW index eligible.
        vectors = (
            self._all(
                """with seeds as (
                 select subject_id, vec from hcg.embeddings
                 where version = hcg.v() and subject_type = 'function'
                   and model = :model and subject_id = any(:seeds)
                   and left(subject_id, 2) = :mode
                 order by subject_id limit 5
               )
               select neighbor.subject_id as token, max(neighbor.similarity) as similarity
               from seeds seed cross join lateral (
                 select subject_id, 1 - (vec <=> seed.vec) as similarity
                 from hcg.embeddings
                 where version = hcg.v() and subject_type = 'function'
                   and model = :model and subject_id <> seed.subject_id
                   and left(subject_id, 2) = :mode
                 order by vec <=> seed.vec, subject_id limit 10
               ) neighbor
               group by neighbor.subject_id
               order by similarity desc, neighbor.subject_id limit 50""",
                model=self.model,
                seeds=seeds[:5],
                mode=mode,
            )
            if seeds
            else []
        )
        return (
            [(row["token"], row["prob"]) for row in graph],
            [(row["token"], row["similarity"]) for row in vectors],
        )

    def similarities(self, previous: str, tokens: list[str]) -> dict[str, float]:
        if not self.model or not tokens:
            return {}
        if len(tokens) > 64:
            raise ValueError("At most 64 scoring candidates are allowed")
        rows = self._all(
            """select candidate.subject_id as token,
                      1 - (candidate.vec <=> previous.vec) as similarity
               from hcg.embeddings previous join hcg.embeddings candidate
                 on candidate.version = previous.version and candidate.model = previous.model
               where previous.version = hcg.v() and previous.subject_type = 'function'
                 and previous.model = :model and previous.subject_id = :previous
                 and candidate.subject_type = 'function' and candidate.subject_id = any(:tokens)
                 and left(candidate.subject_id, 2) = left(previous.subject_id, 2)""",
            model=self.model,
            previous=previous,
            tokens=tokens,
        )
        return {row["token"]: row["similarity"] for row in rows}
