-- F41: corpus percentile norms for the measurable color axes
-- (backend/app/color/features.py), one row per (version, axis, subject_type).
-- Populated by the loader from the `color` pipeline stage's `color.parquet`
-- artifact -- see pipeline/load.py's `color_norms` copy. Runtime
-- normalization (backend/app/color/norms.py's `normalize()`) reads this
-- table by primary key, never aggregates it live.
begin;

create table hcg.color_norms (
    version text not null references hcg.corpus_versions (version) on delete cascade,
    axis text not null,
    subject_type text not null check (subject_type in ('chord', 'transition')),
    count integer not null check (count >= 0),
    p05 double precision not null,
    p25 double precision not null,
    p50 double precision not null,
    p75 double precision not null,
    p95 double precision not null,
    mean double precision not null,
    std double precision not null,
    primary key (version, axis, subject_type)
);
alter table hcg.color_norms enable row level security;

commit;
