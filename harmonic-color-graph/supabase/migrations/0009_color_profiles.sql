-- F43: one color profile per Function (a Roman-token label, e.g. "M:iv"),
-- global Transition (e.g. "M:V>M:I", context = "global" only), or frequent
-- Pattern (a space-joined run of tokens), keyed by (version, subject_type,
-- subject_id). `axes` is a JSON blob with three keys: `raw` (F41's
-- measurable axes for the subject's arrival position), `raw_normalized`
-- (the same, mapped to [0, 1] via hcg.color_norms), and `perceptual` (F42's
-- six axes, each `{value, confidence, source, explanation}`). Populated by
-- the loader from the `color` pipeline stage's `color_profiles.parquet`
-- artifact -- see pipeline/load.py's `color_profiles` copy and
-- backend/app/color/profile.py's `compute_color_profile`, which computes
-- each row.
begin;

create table hcg.color_profiles (
    version text not null references hcg.corpus_versions (version) on delete cascade,
    subject_type text not null check (subject_type in ('function', 'transition', 'pattern')),
    subject_id text not null,
    mode text not null check (mode in ('major', 'minor')),
    support integer not null check (support >= 0),
    axes jsonb not null,
    primary key (version, subject_type, subject_id)
);
alter table hcg.color_profiles enable row level security;

commit;
