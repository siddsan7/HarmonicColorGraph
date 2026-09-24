-- M2 storage correction: integer graph keys and compact edge payloads.
-- The original hcg.edges table remains for migration compatibility; new
-- corpus versions write to edges_compact and graph reads use edges_read.
alter table hcg.corpus_versions
    add column version_key smallint generated always as identity;
create unique index corpus_versions_key_idx on hcg.corpus_versions (version_key);

alter table hcg.nodes
    add column node_key integer generated always as identity;
create unique index nodes_key_idx on hcg.nodes (node_key);

-- Edge type codes: 1 TRANSITIONS_TO, 2 FUNCTIONS_AS,
-- 3 ABS_TRANSITIONS_TO, 4 PATTERN_CONTAINS, 5 HAS_ROOT, 6 HAS_QUALITY.
create table hcg.edges_compact (
    version_key smallint not null references hcg.corpus_versions(version_key) on delete cascade,
    src_key integer not null references hcg.nodes(node_key) on delete cascade,
    dst_key integer not null references hcg.nodes(node_key) on delete cascade,
    type_code smallint not null check (type_code between 1 and 6),
    context_id smallint not null references hcg.contexts(id),
    count integer check (count is null or count >= 0),
    prob real check (prob is null or prob between 0 and 1),
    weight real,
    support integer,
    props jsonb,
    check (support is null or support >= 0)
);
create unique index edges_compact_outgoing_idx on hcg.edges_compact
    (version_key, src_key, type_code, context_id, dst_key);
create index edges_compact_incoming_idx on hcg.edges_compact
    (version_key, dst_key, type_code, context_id, src_key);
alter table hcg.edges_compact enable row level security;

create view hcg.edges_read with (security_invoker = true) as
select cv.version, src.id as src, dst.id as dst,
    case e.type_code
        when 1 then 'TRANSITIONS_TO'
        when 2 then 'FUNCTIONS_AS'
        when 3 then 'ABS_TRANSITIONS_TO'
        when 4 then 'PATTERN_CONTAINS'
        when 5 then 'HAS_ROOT'
        when 6 then 'HAS_QUALITY'
    end as type,
    e.context_id, e.count, e.prob, e.weight,
    case when e.type_code = 1 then
        coalesce(e.props, '{}'::jsonb) ||
        jsonb_build_object('pmi', e.weight, 'support', e.support)
    else coalesce(e.props, '{}'::jsonb) end as props,
    src.type as src_type, dst.type as dst_type
from hcg.edges_compact e
join hcg.corpus_versions cv on cv.version_key = e.version_key
join hcg.nodes src on src.node_key = e.src_key
join hcg.nodes dst on dst.node_key = e.dst_key;
