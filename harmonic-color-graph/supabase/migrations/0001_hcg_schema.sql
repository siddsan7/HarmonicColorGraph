-- F05: hcg schema on Supabase, single migration system (ADR-002, ADR-005).
--
-- Recreates the Phase 1 tables inside a dedicated `hcg` schema (private -
-- never added to the Data API's exposed schemas) with F04's per-context
-- transition columns (genre/section/decade vary independently; there is no
-- combined genre+subgenre+section+decade key). RLS is enabled on every
-- table; since the API is the only reader/writer for now, no policies are
-- added yet (an INFO-level "RLS enabled, no policy" advisory is expected
-- and is not a blocker until app-facing tables need direct browser access).

create schema if not exists hcg;
-- Real Supabase projects pre-provision `extensions`; a plain Postgres
-- instance (e.g. the pgvector/pgvector:pg17 container CI runs migrations
-- against) does not, so create it explicitly rather than assuming it.
create schema if not exists extensions;
create extension if not exists vector with schema extensions;
create extension if not exists pg_trgm with schema extensions;

create table hcg.chords (
    id bigint generated always as identity primary key,
    symbol text not null unique,
    root text,
    quality text,
    pitch_classes jsonb,
    intervals jsonb,
    created_at timestamptz not null default now()
);

create table hcg.roman_chords (
    id bigint generated always as identity primary key,
    roman text not null unique,
    scale_degree integer,
    quality text,
    mode_context text,
    borrowed integer not null default 0,
    borrowed_from text,
    created_at timestamptz not null default now()
);

create table hcg.songs (
    id bigint generated always as identity primary key,
    source_id text not null unique,
    title text,
    artist text,
    spotify_id text,
    genre text,
    release_date text
);

create table hcg.progressions (
    id bigint generated always as identity primary key,
    source text,
    source_song_id text,
    key text,
    mode text,
    genre text,
    subgenre text,
    section text,
    absolute_chords jsonb,
    roman_chords jsonb,
    analysis_confidence double precision,
    parse_warnings jsonb,
    created_at timestamptz not null default now()
);

create table hcg.progression_chords (
    id bigint generated always as identity primary key,
    progression_id bigint not null references hcg.progressions (id) on delete cascade,
    position integer not null,
    absolute_chord text not null,
    roman_chord text
);
create index progression_chords_progression_id_idx on hcg.progression_chords (progression_id);

-- F04: a row varies exactly one of genre/section/decade (or genre+section
-- together) - never a subgenre-bearing composite of all four. The lookup
-- index matches transition_lookup.py's backoff filter shape exactly.
create table hcg.transitions (
    id bigint generated always as identity primary key,
    from_roman text not null,
    to_roman text not null,
    mode_context text,
    genre text,
    subgenre text,
    section text,
    decade integer,
    count integer not null default 0,
    probability double precision,
    relationship_labels jsonb,
    created_at timestamptz not null default now()
);
create index transitions_lookup_idx on hcg.transitions (from_roman, mode_context, genre, section, decade);

create table hcg.genres (
    id bigint generated always as identity primary key,
    name text not null unique
);

create table hcg.sections (
    id bigint generated always as identity primary key,
    name text not null unique
);

create table hcg.theory_labels (
    id bigint generated always as identity primary key,
    name text not null unique,
    description text
);

create table hcg.transition_theory_labels (
    id bigint generated always as identity primary key,
    transition_id bigint not null references hcg.transitions (id) on delete cascade,
    theory_label_id bigint not null references hcg.theory_labels (id) on delete cascade
);

create table hcg.source_metadata (
    id bigint generated always as identity primary key,
    source text not null,
    source_id text not null,
    payload jsonb
);
create index source_metadata_source_id_idx on hcg.source_metadata (source_id);

alter table hcg.chords enable row level security;
alter table hcg.roman_chords enable row level security;
alter table hcg.songs enable row level security;
alter table hcg.progressions enable row level security;
alter table hcg.progression_chords enable row level security;
alter table hcg.transitions enable row level security;
alter table hcg.genres enable row level security;
alter table hcg.sections enable row level security;
alter table hcg.theory_labels enable row level security;
alter table hcg.transition_theory_labels enable row level security;
alter table hcg.source_metadata enable row level security;
