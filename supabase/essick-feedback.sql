-- ESSICK rocker: one shared feedback feed (comments, notes with pins and photos, size answers,
-- "looks right"), on Supabase. Everyone sees everyone's feedback.
-- Run once in the Supabase dashboard: SQL Editor -> New query -> paste -> Run. Safe to run again.
-- Needs essick-comments.sql to have been run first (it made the settings and salt tables).
--
-- The page (viewer/store.js) can only call three functions:
--   essick_feedback_list(p_client)   every visible item; `mine` marks the caller's own
--   essick_feedback_post(...)        add an item, or replace the caller's own item with the same key
--   essick_feedback_delete(...)      delete one of the caller's own items
-- plus upload JPEG photos to the public storage bucket essick-photos.
-- p_client is a random id kept on each device. It is never sent back to anyone, so nobody can
-- change or delete someone else's feedback.
--
-- Spam protection (all here in the database):
--   * plain text, name 1-60 characters, text up to 2000, extra details up to 4 KB, 6 photos
--   * honeypot p_website: filled in = answered like a save, nothing stored
--   * per visitor (SHA-256 of their IP + secret salt; raw IPs never stored), per 10 minutes:
--     10 comments and notes, 200 quick answers; everyone together 600; photos 60
--   * posting on/off switch: essick_settings.posting_enabled '1' / '0'
--
-- Moderating, in the dashboard Table Editor -> essick_feedback:
--   tick `hidden` to take an item off the page, or delete the row. Photos: Storage -> essick-photos.

create table if not exists public.essick_feedback (
  id uuid primary key default gen_random_uuid(),
  client_id uuid not null,
  key text not null check (key ~ '^[A-Za-z0-9_.-]{1,80}$'),
  kind text not null check (kind in ('comment', 'note', 'answer', 'question', 'part_ok')),
  name text not null check (char_length(name) between 1 and 60),
  body text not null default '' check (char_length(body) <= 2000),
  data jsonb not null default '{}' check (jsonb_typeof(data) = 'object' and octet_length(data::text) <= 4096),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  hidden boolean not null default false,
  ip_hash text,
  unique (client_id, key)
);
create index if not exists essick_feedback_created on public.essick_feedback (created_at);
create index if not exists essick_feedback_ip_updated on public.essick_feedback (ip_hash, updated_at);
alter table public.essick_feedback enable row level security;
revoke all on public.essick_feedback from anon, authenticated;

-- Bring over the comments already posted.
insert into public.essick_feedback (id, client_id, key, kind, name, body, created_at, updated_at, hidden, ip_hash)
  select id, gen_random_uuid(), 'comment-' || id, 'comment', name, body, created_at, created_at, hidden, ip_hash
  from public.essick_comments
  on conflict do nothing;

-- The old comment-only functions are replaced by the ones below.
drop function if exists public.essick_comments_list();
drop function if exists public.essick_comment_post(text, text, text);

create or replace function public.essick_ip_hash() returns text
language plpgsql stable security definer set search_path = '' as $$
declare
  h json := coalesce(nullif(current_setting('request.headers', true), ''), '{}')::json;
  ip text := coalesce(nullif(h->>'cf-connecting-ip', ''),
                      nullif(btrim(split_part(h->>'x-forwarded-for', ',', 1)), ''),
                      nullif(h->>'x-real-ip', ''), 'unknown');
begin
  return encode(sha256(convert_to(ip || '|' || (select value from public.essick_private where key = 'ip_salt'), 'UTF8')), 'hex');
end
$$;

create or replace function public.essick_item(f public.essick_feedback, p_client uuid) returns json
language sql stable set search_path = '' as $$
  select json_build_object('id', f.id, 'key', f.key, 'kind', f.kind, 'name', f.name, 'body', f.body, 'data', f.data,
    'created_at', f.created_at, 'updated_at', f.updated_at, 'mine', p_client is not null and f.client_id = p_client)
$$;

create or replace function public.essick_feedback_list(p_client uuid default null) returns json
language sql stable security definer set search_path = '' as $$
  select json_build_object(
    'items', coalesce((
      select json_agg(public.essick_item(f, p_client) order by f.created_at, f.id)
      from (select * from public.essick_feedback where not hidden order by created_at, id limit 5000) f
    ), '[]'::json),
    'postingEnabled', coalesce((select value from public.essick_settings where key = 'posting_enabled'), '1') <> '0'
  )
$$;

create or replace function public.essick_feedback_post(
  p_client uuid, p_key text, p_kind text, p_name text, p_body text default '', p_data jsonb default '{}', p_website text default '')
returns json
language plpgsql volatile security definer set search_path = '' as $$
declare
  v_name text := public.essick_clean(p_name);
  v_body text := public.essick_clean(p_body);
  v_data jsonb := coalesce(p_data, '{}'::jsonb);
  v_hash text;
  v_text boolean := p_kind in ('comment', 'note');
  v_row public.essick_feedback;
begin
  -- Errors use PostgREST's PTxxx codes, which become that HTTP status for the page.
  if p_client is null or p_key is null or p_key !~ '^[A-Za-z0-9_.-]{1,80}$' then
    raise sqlstate 'PT400' using message = 'Reload the page and try again.';
  end if;
  if p_kind is null or p_kind not in ('comment', 'note', 'answer', 'question', 'part_ok') then
    raise sqlstate 'PT400' using message = 'Reload the page and try again.';
  end if;
  if char_length(v_name) not between 1 and 60 then
    raise sqlstate 'PT400' using message = 'Name must be 1 to 60 characters.';
  end if;
  if char_length(v_body) > 2000 then
    raise sqlstate 'PT400' using message = 'That is too long. Keep it under 2000 characters.';
  end if;
  if p_kind = 'comment' and v_body = '' then
    raise sqlstate 'PT400' using message = 'Write a comment first.';
  end if;
  if jsonb_typeof(v_data) <> 'object' or octet_length(v_data::text) > 4096 then
    raise sqlstate 'PT400' using message = 'That is too long.';
  end if;
  if v_data ? 'photos' and (jsonb_typeof(v_data->'photos') <> 'array' or jsonb_array_length(v_data->'photos') > 6
      or exists (select 1 from jsonb_array_elements(v_data->'photos') p
                 where jsonb_typeof(p) <> 'string' or (p #>> '{}') !~ '^[0-9a-f-]{36}\.jpg$')) then
    raise sqlstate 'PT400' using message = 'Up to 6 photos.';
  end if;

  -- Honeypot: answer exactly like a save, store nothing.
  if btrim(coalesce(p_website, '')) <> '' then
    return json_build_object('ok', true, 'item', json_build_object('id', gen_random_uuid(), 'key', p_key, 'kind', p_kind,
      'name', v_name, 'body', v_body, 'data', v_data, 'created_at', now(), 'updated_at', now(), 'mine', true));
  end if;

  if coalesce((select value from public.essick_settings where key = 'posting_enabled'), '1') = '0' then
    raise sqlstate 'PT403' using message = 'Feedback is closed for now.';
  end if;

  v_hash := public.essick_ip_hash();
  if (select count(*) from public.essick_feedback where ip_hash = v_hash and updated_at > now() - interval '10 minutes'
        and (kind in ('comment', 'note')) = v_text) >= (case when v_text then 10 else 200 end) then
    raise sqlstate 'PT429' using message = 'You have sent a lot in a short time. Please wait a few minutes.';
  end if;
  if (select count(*) from public.essick_feedback where updated_at > now() - interval '10 minutes') >= 600 then
    raise sqlstate 'PT429' using message = 'Lots of feedback right now. Please try again in a few minutes.';
  end if;

  insert into public.essick_feedback as f (client_id, key, kind, name, body, data, ip_hash)
    values (p_client, p_key, p_kind, v_name, v_body, v_data, v_hash)
  on conflict (client_id, key) do update
    set kind = excluded.kind, name = excluded.name, body = excluded.body, data = excluded.data,
        ip_hash = excluded.ip_hash, updated_at = now()
  returning * into v_row;
  return json_build_object('ok', true, 'item', public.essick_item(v_row, p_client));
end
$$;

create or replace function public.essick_feedback_delete(p_client uuid, p_key text) returns json
language sql volatile security definer set search_path = '' as $$
  with d as (delete from public.essick_feedback where client_id = p_client and key = p_key returning 1)
  select json_build_object('ok', true, 'deleted', (select count(*) from d))
$$;

revoke all on function public.essick_ip_hash(), public.essick_item(public.essick_feedback, uuid) from public, anon, authenticated;
revoke all on function public.essick_feedback_list(uuid), public.essick_feedback_post(uuid, text, text, text, text, jsonb, text),
  public.essick_feedback_delete(uuid, text) from public, anon, authenticated;
grant execute on function public.essick_feedback_list(uuid), public.essick_feedback_post(uuid, text, text, text, text, jsonb, text),
  public.essick_feedback_delete(uuid, text) to anon, authenticated;

-- Photos: a public bucket anyone can add JPEGs to (up to 3 MB each, named <uuid>.jpg, at most 60
-- across everyone per 10 minutes). Nobody but you can change or delete them.
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
  values ('essick-photos', 'essick-photos', true, 3145728, array['image/jpeg'])
  on conflict (id) do update set public = true, file_size_limit = 3145728, allowed_mime_types = array['image/jpeg'];

create or replace function public.essick_photo_quota_ok() returns boolean
language sql stable security definer set search_path = '' as $$
  select count(*) < 60 from storage.objects where bucket_id = 'essick-photos' and created_at > now() - interval '10 minutes'
$$;
revoke all on function public.essick_photo_quota_ok() from public;
grant execute on function public.essick_photo_quota_ok() to anon, authenticated;

drop policy if exists "essick photos: anyone can add" on storage.objects;
create policy "essick photos: anyone can add" on storage.objects for insert to anon, authenticated
  with check (bucket_id = 'essick-photos' and name ~ '^[0-9a-f-]{36}\.jpg$' and public.essick_photo_quota_ok());
