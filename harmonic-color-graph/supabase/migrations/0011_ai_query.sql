-- F73: private assistant audit trail and atomic per-IP hourly counters.
-- 0005 is already occupied by the compact-edge migration in this repository.
begin;

create table hcg.ai_query_logs (
    query_id uuid primary key,
    created_at timestamptz not null default now(),
    ip_hash text not null,
    user_query text not null,
    parsed_intent jsonb,
    route text,
    tools jsonb,
    final jsonb,
    validation_errors jsonb,
    error_category text,
    model text,
    tokens_in integer not null default 0 check (tokens_in >= 0),
    tokens_out integer not null default 0 check (tokens_out >= 0),
    cost_usd numeric(12, 8) not null default 0 check (cost_usd >= 0),
    latency_ms integer not null default 0 check (latency_ms >= 0)
);
create index ai_query_logs_created_at_idx on hcg.ai_query_logs (created_at);
alter table hcg.ai_query_logs enable row level security;

create table hcg.rate_limits (
    key text not null,
    window_start timestamptz not null,
    count integer not null default 0 check (count >= 0),
    primary key (key, window_start)
);
create index rate_limits_window_start_idx on hcg.rate_limits (window_start);
alter table hcg.rate_limits enable row level security;

commit;
