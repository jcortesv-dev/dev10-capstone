
set search_path to characters;

-- 1) What's the most played class?
-- Counts distinct characters per class to avoid over-counting duplicate class rows.
select
  cc.class,
  count(distinct cc.char_id) as character_count
from character_class cc
group by cc.class
order by character_count desc;


-- 2) What's the most played race?
select
  c.race,
  count(*) as character_count
from character c
where c.race is not null and c.race <> ''
group by c.race
order by character_count desc;


-- 3) How many characters multiclass?
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


-- 4) How many characters get to level 20?
select
  count(*) as level_20_characters
from character
where total_level = 20;


-- 5) Most popular stat to max?
-- "Maxed" definition: stat >= 20.
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
group by stat_name
order by maxed_count desc;


-- 6) Most popular dump stat?
-- Dump stat = minimum stat on a character. Ties are all counted.
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
group by stat_name
order by dump_count desc;


-- 7) Any correlation between classes and note-taking length?
select
  cc.class,
  count(distinct c.char_id) as characters,
  avg(c.notes_len) as avg_notes_len,
  percentile_cont(0.5) within group (order by c.notes_len) as median_notes_len
from character c
join character_class cc on cc.char_id = c.char_id
where c.notes_len is not null
group by cc.class
order by avg_notes_len desc;


-- 8) Most popular subclass per class?
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
where rn = 1
order by class;
