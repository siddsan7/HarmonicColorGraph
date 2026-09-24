-- F27: durable work ledger. Redis carries wakeups; Postgres owns job truth.
create table hcg.jobs (
    id uuid primary key default gen_random_uuid(),
    type text not null check (type in ('graph_rebuild', 'embedding_rebuild', 'evaluation_run')),
    status text not null default 'queued' check (
        status in ('queued', 'running', 'retrying', 'completed', 'failed', 'dead_letter', 'cancelled')
    ),
    payload jsonb not null,
    result jsonb,
    progress real not null default 0 check (progress between 0 and 1),
    stage text,
    processed integer check (processed is null or processed >= 0),
    total integer check (total is null or total >= 0),
    attempt integer not null default 0 check (attempt >= 0),
    max_attempts integer not null default 1 check (max_attempts >= 1),
    idempotency_key text,
    created_at timestamptz not null default now(),
    queued_at timestamptz not null default now(),
    started_at timestamptz,
    completed_at timestamptz,
    failed_at timestamptz,
    last_error_code text,
    last_error_message text,
    worker_id text,
    lease_expires_at timestamptz
);
create index jobs_status_created_idx on hcg.jobs (status, created_at);
create index jobs_worker_idx on hcg.jobs (worker_id) where status = 'running';
alter table hcg.jobs enable row level security;

create table hcg.job_events (
    id bigint generated always as identity primary key,
    job_id uuid not null references hcg.jobs(id) on delete cascade,
    status text not null,
    stage text,
    progress real not null default 0,
    processed integer,
    total integer,
    created_at timestamptz not null default now()
);
create index job_events_job_id_idx on hcg.job_events (job_id, id);
alter table hcg.job_events enable row level security;
