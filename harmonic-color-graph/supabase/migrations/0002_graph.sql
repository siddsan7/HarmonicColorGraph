-- F23: versioned harmonic graph and evidence, kept in the private hcg schema.
-- F24 loads a complete version before changing the single active row.

create table hcg.corpus_versions (
    version text primary key,
    manifest jsonb not null,
    active boolean not null default false,
    loaded_at timestamptz not null default now()
);
create unique index corpus_versions_one_active_idx
    on hcg.corpus_versions (active) where active;

-- IDs are stable across corpus versions. ID 0 denotes the global context.
create table hcg.contexts (
    id smallint primary key,
    type text not null,
    value text not null,
    label text not null,
    unique (type, value)
);

create table hcg.nodes (
    version text not null references hcg.corpus_versions (version) on delete cascade,
    id text not null,
    type text not null,
    label text not null,
    props jsonb not null default '{}'::jsonb,
    primary key (version, id)
);
create index nodes_version_type_idx on hcg.nodes (version, type);

create table hcg.edges (
    version text not null,
    src text not null,
    dst text not null,
    type text not null,
    context_id smallint not null references hcg.contexts (id),
    count integer,
    prob real,
    weight real,
    props jsonb not null default '{}'::jsonb,
    primary key (version, type, context_id, src, dst),
    foreign key (version, src) references hcg.nodes (version, id) on delete cascade,
    foreign key (version, dst) references hcg.nodes (version, id) on delete cascade,
    check (count is null or count >= 0),
    check (prob is null or prob between 0 and 1)
);
create index edges_version_src_type_context_idx
    on hcg.edges (version, src, type, context_id);
create index edges_version_dst_type_idx on hcg.edges (version, dst, type);
create index edges_context_id_idx on hcg.edges (context_id);

create table hcg.ngram_histories (
    version text not null references hcg.corpus_versions (version) on delete cascade,
    context_id smallint not null references hcg.contexts (id),
    ord smallint not null check (ord between 1 and 5),
    history text not null,
    total integer not null check (total >= 0),
    distinct_next integer not null check (distinct_next >= 0),
    next jsonb not null,
    cont jsonb not null,
    primary key (version, context_id, ord, history)
);
create index ngram_histories_context_id_idx on hcg.ngram_histories (context_id);

create table hcg.patterns (
    version text not null references hcg.corpus_versions (version) on delete cascade,
    pattern text not null,
    length smallint not null check (length between 3 and 8),
    support integer not null check (support >= 0),
    song_count integer not null check (song_count >= 0),
    rotations_observed smallint[] not null default '{}',
    context_lifts jsonb not null default '{}'::jsonb,
    primary key (version, pattern)
);
create index patterns_version_support_idx on hcg.patterns (version, support desc);

create table hcg.song_refs (
    version text not null references hcg.corpus_versions (version) on delete cascade,
    song_id text not null,
    spotify_id text,
    genre text,
    decade text,
    primary key (version, song_id)
);

create table hcg.pattern_examples (
    version text not null,
    pattern text not null,
    song_id text not null,
    section text,
    ordinal integer not null,
    position integer check (position is null or position >= 0),
    rank smallint not null check (rank > 0),
    primary key (version, pattern, rank),
    foreign key (version, pattern) references hcg.patterns (version, pattern) on delete cascade,
    foreign key (version, song_id) references hcg.song_refs (version, song_id) on delete cascade
);
create index pattern_examples_version_song_idx on hcg.pattern_examples (version, song_id);

-- Examples for the most frequent transitions are produced by F22 as a
-- separate artifact and consumed by the graph evidence API in F26.
create table hcg.transition_examples (
    version text not null references hcg.corpus_versions (version) on delete cascade,
    from_token text not null,
    to_token text not null,
    song_id text not null,
    section text,
    ordinal integer not null,
    position integer check (position is null or position >= 0),
    rank smallint not null check (rank > 0),
    primary key (version, from_token, to_token, rank),
    foreign key (version, song_id) references hcg.song_refs (version, song_id) on delete cascade
);
create index transition_examples_version_song_idx on hcg.transition_examples (version, song_id);

create table hcg.relationship_types (
    version text not null references hcg.corpus_versions (version) on delete cascade,
    id text not null,
    label text not null,
    props jsonb not null default '{}'::jsonb,
    primary key (version, id)
);

-- Fact IDs are stable within a version. The composite key lets a staged
-- version reuse citations while the prior active version remains available.
create table hcg.facts (
    fact_id text not null,
    version text not null references hcg.corpus_versions (version) on delete cascade,
    kind text not null,
    subject text not null,
    template text not null,
    params jsonb not null default '{}'::jsonb,
    primary key (version, fact_id)
);
create index facts_version_subject_idx on hcg.facts (version, subject);

create view hcg.active_version with (security_invoker = true) as
select version, loaded_at from hcg.corpus_versions where active;

create function hcg.v() returns text
language sql stable security invoker
set search_path = hcg, pg_temp
as $$ select version from hcg.corpus_versions where active $$;

alter table hcg.corpus_versions enable row level security;
alter table hcg.contexts enable row level security;
alter table hcg.nodes enable row level security;
alter table hcg.edges enable row level security;
alter table hcg.ngram_histories enable row level security;
alter table hcg.patterns enable row level security;
alter table hcg.song_refs enable row level security;
alter table hcg.pattern_examples enable row level security;
alter table hcg.transition_examples enable row level security;
alter table hcg.relationship_types enable row level security;
alter table hcg.facts enable row level security;
