-- F51: versioned 64-dimensional vectors and materialized function neighbors.
-- The hcg schema is private; API reads use the direct database role.
begin;

create extension if not exists vector with schema extensions;

create table hcg.embeddings (
    version text not null references hcg.corpus_versions (version) on delete cascade,
    subject_type text not null check (subject_type in ('function', 'pattern')),
    subject_id text not null,
    model text not null,
    vec extensions.vector(64) not null,
    created_at timestamptz not null default now(),
    primary key (version, subject_type, model, subject_id)
);
create index embeddings_function_cosine_idx on hcg.embeddings
    using hnsw (vec extensions.vector_cosine_ops)
    where subject_type = 'function';
create index embeddings_pattern_cosine_idx on hcg.embeddings
    using hnsw (vec extensions.vector_cosine_ops)
    where subject_type = 'pattern';
alter table hcg.embeddings enable row level security;

alter table hcg.edges_compact drop constraint edges_compact_type_code_check;
alter table hcg.edges_compact add constraint edges_compact_type_code_check
    check (type_code between 1 and 8);

create or replace view hcg.edges_read with (security_invoker = true) as
select cv.version, src.id as src, dst.id as dst,
    case e.type_code
        when 1 then 'TRANSITIONS_TO'
        when 2 then 'FUNCTIONS_AS'
        when 3 then 'ABS_TRANSITIONS_TO'
        when 4 then 'PATTERN_CONTAINS'
        when 5 then 'HAS_ROOT'
        when 6 then 'HAS_QUALITY'
        when 7 then 'VOICE_LEADS_TO'
        when 8 then 'SIMILAR_TO'
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

commit;
