-- F40: VOICE_LEADS_TO edges (minimal-motion voice leading between top
-- absolute chord transitions), computed once from music theory rather than
-- corpus statistics. Extends the compact edge type-code range from 6 to 7.
alter table hcg.edges_compact
    drop constraint edges_compact_type_code_check;
alter table hcg.edges_compact
    add constraint edges_compact_type_code_check check (type_code between 1 and 7);

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
