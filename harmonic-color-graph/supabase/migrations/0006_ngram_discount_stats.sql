-- F32: precompute Kneser-Ney count-of-counts for each corpus/context/order.
-- Expanding jsonb for these values during a public request exceeds the
-- serverless statement timeout on the full corpus. This migration also
-- backfills the currently active corpus; future loads populate the table
-- before switching the active version.
begin;
set local statement_timeout = '20min';

create table hcg.ngram_discount_stats (
    version text not null references hcg.corpus_versions(version) on delete cascade,
    context_id smallint not null references hcg.contexts(id),
    ord smallint not null check (ord between 2 and 5),
    n1 integer not null check (n1 >= 0),
    n2 integer not null check (n2 >= 0),
    primary key (version, context_id, ord)
);
alter table hcg.ngram_discount_stats enable row level security;

insert into hcg.ngram_discount_stats (version, context_id, ord, n1, n2)
select h.version, h.context_id, h.ord,
       count(*) filter (where kv.value::integer = 1),
       count(*) filter (where kv.value::integer = 2)
from hcg.ngram_histories h
cross join lateral jsonb_each_text(h.next) kv
where h.ord > 1
group by h.version, h.context_id, h.ord;

commit;
