set search_path to characters;

drop view if exists vw_class_popularity;
create view vw_class_popularity as
select
  cc.class,
  count(distinct cc.char_id) as character_count
from character_class cc
group by cc.class;


drop view if exists vw_race_popularity;
create view vw_race_popularity as
select
  c.race,
  count(*) as character_count
from character c
where c.race is not null and c.race <> ''
group by c.race;


drop view if exists vw_multiclass_count;
create view vw_multiclass_count as
with class_counts as (
  select
    char_id,
    count(*) as class_count
  from character_class
  group by char_id
)
select
  count(*) as multiclass_characters
from class_counts
where class_count > 1;


drop view if exists vw_level_20_count;
create view vw_level_20_count as
select
  count(*) as level_20_characters
from character
where total_level = 20;


drop view if exists vw_maxed_stats;
create view vw_maxed_stats as
with stats as (
  select 'str' as stat_name, str as stat_value from character
  union all select 'dex', dex from character
  union all select 'con', con from character
  union all select 'int', int from character
  union all select 'wis', wis from character
  union all select 'cha', cha from character
)
select
  stat_name,
  count(*) as maxed_count
from stats
where stat_value >= 20
group by stat_name;


drop view if exists vw_dump_stats;
create view vw_dump_stats as
with per_char_stats as (
  select
    c.char_id,
    v.stat_name,
    v.stat_value,
    least(c.str, c.dex, c.con, c.int, c.wis, c.cha) as min_stat
  from character c
  cross join lateral (
    values
      ('str', c.str),
      ('dex', c.dex),
      ('con', c.con),
      ('int', c.int),
      ('wis', c.wis),
      ('cha', c.cha)
  ) as v(stat_name, stat_value)
)
select
  stat_name,
  count(*) as dump_count
from per_char_stats
where stat_value = min_stat
group by stat_name;


drop view if exists vw_class_notes_summary;
create view vw_class_notes_summary as
select
  cc.class,
  count(distinct c.char_id) as characters,
  avg(c.notes_len) as avg_notes_len,
  percentile_cont(0.5) within group (order by c.notes_len) as median_notes_len
from character c
join character_class cc on cc.char_id = c.char_id
where c.notes_len is not null
group by cc.class;


drop view if exists vw_top_subclass_per_class;
create view vw_top_subclass_per_class as
with subclass_counts as (
  select
    class,
    subclass,
    count(*) as subclass_count
  from character_class
  where subclass is not null and subclass <> ''
  group by class, subclass
),
ranked as (
  select
    class,
    subclass,
    subclass_count,
    row_number() over (
      partition by class
      order by subclass_count desc, subclass
    ) as rn
  from subclass_counts
)
select
  class,
  subclass as most_popular_subclass,
  subclass_count
from ranked
where rn = 1;


drop view if exists vw_dashboard_kpis;
create view vw_dashboard_kpis as
select
  (select count(*) from character) as total_characters,
  (select multiclass_characters from vw_multiclass_count) as multiclass_characters,
  (select level_20_characters from vw_level_20_count) as level_20_characters,
  (select avg(total_level) from character where total_level is not null) as avg_total_level;
