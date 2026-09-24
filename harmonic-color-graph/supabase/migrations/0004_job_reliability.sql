-- F29: durable idempotency and bounded job retries.
alter table hcg.jobs alter column max_attempts set default 3;
alter table hcg.jobs add column available_at timestamptz not null default now();
alter table hcg.jobs add column request_hash text;
create index jobs_ready_idx on hcg.jobs (available_at, created_at)
    where status in ('queued', 'retrying');
create index jobs_expired_lease_idx on hcg.jobs (lease_expires_at)
    where status = 'running';

create table hcg.idempotency_keys (
    key text primary key,
    operation text not null,
    request_hash text not null,
    job_id uuid not null references hcg.jobs(id) on delete cascade,
    created_at timestamptz not null default now(),
    expires_at timestamptz not null default now() + interval '7 days'
);
create index idempotency_keys_expires_idx on hcg.idempotency_keys (expires_at);
alter table hcg.idempotency_keys enable row level security;
