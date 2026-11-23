-- ESSICK rocker comments, on Supabase.
-- Run this once in the Supabase dashboard: SQL Editor -> New query -> paste -> Run.
-- Safe to run again (it only adds what is missing and replaces the two functions).
--
-- The page (viewer/comments.js) can do exactly two things, both through functions:
--   essick_comments_list()                       visible comments, oldest first, never ip_hash
--   essick_comment_post(p_name, p_body, p_website) add one comment
-- The tables themselves are locked: the public key cannot read or write them directly.
--
-- Spam protection, all enforced here in the database:
--   * plain text only: trimmed, control and bidi-override characters removed
--   * name 1-60 characters, comment 1-2000
--   * honeypot: p_website is a field people never see; filled in = answered like a save,
--     nothing stored
--   * at most 5 posts per visitor per 10 minutes (visitor = SHA-256 of their IP plus a
--     random salt kept in this database; raw IPs are never stored), and at most 60
--     posts from everyone together per 10 minutes
--   * a posting on/off switch: essick_settings, key posting_enabled, '1' or '0'
--
-- Moderating, in the dashboard Table Editor:
--   essick_comments: tick `hidden` to take a comment off the page, or delete the row
--   essick_settings: set posting_enabled to '0' to close posting (people can still read)

create table if not exists public.essick_comments (
  id uuid primary key default gen_random_uuid(),
  name text not null check (char_length(name) between 1 and 60),
  body text not null check (char_length(body) between 1 and 2000),
  created_at timestamptz not null default now(),
  hidden boolean not null default false,
  ip_hash text
);
create index if not exists essick_comments_created on public.essick_comments (created_at);
create index if not exists essick_comments_ip_created on public.essick_comments (ip_hash, created_at);

create table if not exists public.essick_settings (
  key text primary key,
  value text
);
insert into public.essick_settings (key, value) values ('posting_enabled', '1') on conflict (key) do nothing;

-- The salt for hashing IPs. Never sent to anyone.
create table if not exists public.essick_private (
  key text primary key,
  value text not null
);
insert into public.essick_private (key, value)
  values ('ip_salt', replace(gen_random_uuid()::text || gen_random_uuid()::text, '-', ''))
  on conflict (key) do nothing;

-- Lock the tables. Row level security with no policies = the public key sees nothing.
alter table public.essick_comments enable row level security;
alter table public.essick_settings enable row level security;
alter table public.essick_private enable row level security;
revoke all on public.essick_comments, public.essick_settings, public.essick_private from anon, authenticated;

-- Plain text: \r\n -> \n, drop control characters (keeping newline and tab) and
-- zero-width / bidi-override characters, trim.
create or replace function public.essick_clean(t text) returns text
language sql immutable set search_path = '' as $$
  select btrim(
    regexp_replace(
      replace(replace(coalesce(t, ''), E'\r\n', E'\n'), E'\r', E'\n'),
      '[\x01-\x08\x0B-\x1F\x7F\u200B-\u200F\u202A-\u202E\u2066-\u2069]', '', 'g'),
    E' \t\n' || chr(160))
$$;

create or replace function public.essick_comments_list() returns json
language sql stable security definer set search_path = '' as $$
  select json_build_object(
    'comments', coalesce((
      select json_agg(json_build_object('id', c.id, 'name', c.name, 'body', c.body, 'created_at', c.created_at)
                      order by c.created_at, c.id)
      from (select * from public.essick_comments where not hidden order by created_at, id limit 1000) c
    ), '[]'::json),
    'postingEnabled', coalesce((select value from public.essick_settings where key = 'posting_enabled'), '1') <> '0'
  )
$$;

create or replace function public.essick_comment_post(p_name text, p_body text, p_website text default '')
returns json
language plpgsql volatile security definer set search_path = '' as $$
declare
  v_name text := public.essick_clean(p_name);
  v_body text := public.essick_clean(p_body);
  v_headers json;
  v_ip text;
  v_hash text;
  v_row public.essick_comments;
begin
  -- Errors use PostgREST's PTxxx codes, which become that HTTP status for the page.
  if char_length(v_name) not between 1 and 60 then
    raise sqlstate 'PT400' using message = 'Name must be 1 to 60 characters.';
  end if;
  if char_length(v_body) not between 1 and 2000 then
    raise sqlstate 'PT400' using message = 'Comment must be 1 to 2000 characters.';
  end if;

  -- Honeypot: answer exactly like a save, store nothing.
  if btrim(coalesce(p_website, '')) <> '' then
    return json_build_object('ok', true, 'comment',
      json_build_object('id', gen_random_uuid(), 'name', v_name, 'body', v_body, 'created_at', now()));
  end if;

  if coalesce((select value from public.essick_settings where key = 'posting_enabled'), '1') = '0' then
    raise sqlstate 'PT403' using message = 'Comments are closed for now.';
  end if;

  v_headers := coalesce(nullif(current_setting('request.headers', true), ''), '{}')::json;
  v_ip := coalesce(nullif(v_headers->>'cf-connecting-ip', ''),
                   nullif(btrim(split_part(v_headers->>'x-forwarded-for', ',', 1)), ''),
                   nullif(v_headers->>'x-real-ip', ''),
                   'unknown');
  v_hash := encode(sha256(convert_to(v_ip || '|' || (select value from public.essick_private where key = 'ip_salt'), 'UTF8')), 'hex');

  if (select count(*) from public.essick_comments where ip_hash = v_hash and created_at > now() - interval '10 minutes') >= 5 then
    raise sqlstate 'PT429' using message = 'You have posted a lot in a short time. Please wait a few minutes.';
  end if;
  if (select count(*) from public.essick_comments where created_at > now() - interval '10 minutes') >= 60 then
    raise sqlstate 'PT429' using message = 'Lots of comments right now. Please try again in a few minutes.';
  end if;

  insert into public.essick_comments (name, body, ip_hash) values (v_name, v_body, v_hash)
    returning * into v_row;
  return json_build_object('ok', true, 'comment',
    json_build_object('id', v_row.id, 'name', v_row.name, 'body', v_row.body, 'created_at', v_row.created_at));
end
$$;

revoke all on function public.essick_clean(text), public.essick_comments_list(), public.essick_comment_post(text, text, text) from public, anon, authenticated;
grant execute on function public.essick_comments_list(), public.essick_comment_post(text, text, text) to anon, authenticated;
