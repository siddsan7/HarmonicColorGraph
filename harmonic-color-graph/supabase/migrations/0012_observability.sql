-- F75: private, bounded fields for API traffic and latency diagnostics.
begin;

create table hcg.api_request_logs (
    id bigint generated always as identity primary key,
    occurred_at timestamptz not null default now(),
    trace_id char(32) not null,
    request_id uuid not null,
    route text not null,
    method text not null,
    status smallint not null check (status between 100 and 599),
    latency_ms double precision not null check (latency_ms >= 0)
);
create index api_request_logs_occurred_at_idx on hcg.api_request_logs (occurred_at desc);
alter table hcg.api_request_logs enable row level security;

-- Preserve each model's calls and tokens; the legacy model column holds only
-- the last model used by a multi-model assistant request.
alter table hcg.ai_query_logs
    add column model_usage jsonb not null default '{}'::jsonb;

commit;
