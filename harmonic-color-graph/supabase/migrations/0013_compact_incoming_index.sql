-- Node keys are globally unique, so destination lookups do not need the
-- version prefix. Keep version predicates in queries for corpus isolation.
-- Omitting the source suffix lets B-tree deduplication pack repeated incoming
-- destinations; outgoing uniqueness remains enforced by its original index.
drop index hcg.edges_compact_incoming_idx;
create index edges_compact_incoming_idx on hcg.edges_compact
    (dst_key, type_code, context_id);
