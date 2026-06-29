drop schema if exists characters cascade;

create schema characters;
set search_path to characters;

create table character (
    char_id bigint generated always as identity primary key,
    source_id text,
    name text,
    race text,
    background text,
    total_level smallint,
    hp smallint,
    str smallint,
    dex smallint,
    con smallint,
    int smallint,
    wis smallint,
    cha smallint,
    notes_len int,
    recorded_at timestamptz
);

create table character_class (
    class_id bigint generated always as identity primary key,
    char_id bigint not null references character (char_id) on delete cascade,
    class text not null,
    subclass text,
    level smallint
);

create table character_feats(
    feat_id bigint generated always as identity primary key,
    char_id bigint not null references character (char_id) on delete cascade,
    feat text not null
);
