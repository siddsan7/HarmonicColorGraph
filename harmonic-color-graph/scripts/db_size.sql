select n.nspname, pg_size_pretty(sum(pg_total_relation_size(c.oid))) as size
from pg_class c join pg_namespace n on n.oid = c.relnamespace
where n.nspname in ('hcg','public') and c.relkind in ('r','m','i')
group by 1;
select pg_size_pretty(pg_database_size(current_database())) as database_size;
