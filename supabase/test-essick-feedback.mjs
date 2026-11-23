// Checks essick-comments.sql + essick-feedback.sql in a real (in-memory) Postgres, acting as Supabase's public role.
// Run from a scratch folder: npm i @electric-sql/pglite && node <this file> <path to supabase/>
import {PGlite} from '@electric-sql/pglite';
import {readFileSync} from 'node:fs';
import assert from 'node:assert/strict';
const dir = process.argv[2];
const db = new PGlite();
await db.exec(`create role anon nologin; create role authenticated nologin; grant usage on schema public to anon, authenticated;
  create schema storage; grant usage on schema storage to anon, authenticated;
  create table storage.buckets (id text primary key, name text, public boolean, file_size_limit bigint, allowed_mime_types text[]);
  create table storage.objects (id uuid primary key default gen_random_uuid(), bucket_id text, name text, created_at timestamptz default now());`);
await db.exec(readFileSync(dir + '/essick-comments.sql', 'utf8'));
await db.exec(`insert into essick_comments (id, name, body, created_at) values (gen_random_uuid(), 'Old', 'earlier comment', '2026-11-20')`);
const fb = readFileSync(dir + '/essick-feedback.sql', 'utf8');
await db.exec(fb); await db.exec(fb); // twice: safe to re-run, and the old comment is copied once
const as = async (ip, q, params = []) => {
  await db.exec(`reset role`);
  await db.query(`select set_config('request.headers', $1, false)`, [JSON.stringify({'cf-connecting-ip': ip})]);
  await db.exec(`set role anon`);
  try { return (await db.query(q, params)).rows; } finally { await db.exec(`reset role`); }
};
const A = '11111111-1111-4111-8111-111111111111', B = '22222222-2222-4222-8222-222222222222';
const post = (ip, client, key, kind, name, body = '', data = {}, website = '') =>
  as(ip, `select essick_feedback_post($1,$2,$3,$4,$5,$6::jsonb,$7) as r`, [client, key, kind, name, body, JSON.stringify(data), website]).then(r => r[0].r);
const code = async (p) => { try { await p; return 'ok'; } catch (e) { return e.code; } };
const list = (client = null) => as('1.1.1.1', `select essick_feedback_list($1) as r`, [client]).then(r => r[0].r);

let l = await list();
assert.equal(l.items.length, 1); assert.equal(l.items[0].kind, 'comment'); assert.equal(l.items[0].body, 'earlier comment');
assert.equal((await code(as('1.1.1.1', `select essick_comments_list()`))), '42883'); // old function gone

// everyone sees everyone; mine marks the caller's
let r = await post('10.0.0.1', A, 'note-1', 'note', ' Ada ', ' Arm too thick\r\n', {part: 'ARM_R', point: [1, 2, 3], what: 'too thick', photos: ['aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa.jpg']});
assert.equal(r.item.name, 'Ada'); assert.equal(r.item.body, 'Arm too thick'); assert.equal(r.item.mine, true);
await post('10.0.0.2', B, 'answer-seat_w', 'answer', 'Ben', '', {dimId: 'seat_w', verdict: 'right'});
l = await list(B);
assert.deepEqual(l.items.map(i => [i.name, i.mine]), [['Old', false], ['Ada', false], ['Ben', true]]);
assert.ok(!JSON.stringify(l).includes(A) && !JSON.stringify(l).includes(B), 'client ids never returned');
assert.ok(!JSON.stringify(l).includes('ip_hash'));
// re-answering replaces your own answer, not someone else's
await post('10.0.0.2', B, 'answer-seat_w', 'answer', 'Ben', '', {dimId: 'seat_w', verdict: 'wrong', value_mm: 500});
await post('10.0.0.1', A, 'answer-seat_w', 'answer', 'Ada', '', {dimId: 'seat_w', verdict: 'right'});
l = await list();
assert.deepEqual(l.items.filter(i => i.kind === 'answer').map(i => [i.name, i.data.verdict]), [['Ben', 'wrong'], ['Ada', 'right']]);
// delete only your own
assert.equal((await as('9.9.9.9', `select essick_feedback_delete($1, 'note-1') as r`, [B]))[0].r.deleted, 0);
assert.equal((await as('9.9.9.9', `select essick_feedback_delete($1, 'note-1') as r`, [A]))[0].r.deleted, 1);
// validation
for (const args of [[A, 'bad key!', 'note', 'A'], [A, 'k', 'evil', 'A'], [A, 'k', 'note', ''], [A, 'k', 'note', 'x'.repeat(61)],
  [A, 'k', 'comment', 'A', '  '], [A, 'k', 'note', 'A', 'x'.repeat(2001)], [A, 'k', 'note', 'A', '', {big: 'x'.repeat(5000)}],
  [A, 'k', 'note', 'A', '', {photos: ['../evil.jpg']}], [A, 'k', 'note', 'A', '', {photos: Array(7).fill('aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa.jpg')}]])
  assert.equal(await code(post('9.9.9.9', ...args)), 'PT400', JSON.stringify(args).slice(0, 80));
assert.equal(await code(as('9.9.9.9', `select essick_feedback_post(null, 'k', 'note', 'A')`)), 'PT400');
// honeypot
const n0 = (await db.query(`select count(*)::int n from essick_feedback`)).rows[0].n;
r = await post('8.8.8.8', A, 'c-bot', 'comment', 'Bot', 'Buy now', {}, 'https://spam.test'); assert.equal(r.ok, true);
assert.equal((await db.query(`select count(*)::int n from essick_feedback`)).rows[0].n, n0);
// rate limits: 10 comments+notes, separately 200 quick answers, per visitor per 10 minutes
for (let i = 0; i < 10; i++) assert.equal(await code(post('7.7.7.7', A, 'c' + i, 'comment', 'A', 'hi ' + i)), 'ok');
assert.equal(await code(post('7.7.7.7', A, 'c10', 'comment', 'A', 'eleventh')), 'PT429');
assert.equal(await code(post('7.7.7.7', A, 'a1', 'answer', 'A', '', {verdict: 'right'})), 'ok');
assert.equal(await code(post('6.6.6.6', B, 'c0', 'comment', 'B', 'other visitor')), 'ok');
await db.exec(`update essick_feedback set updated_at = now() - interval '1 hour'`);
assert.equal(await code(post('7.7.7.7', A, 'c10', 'comment', 'A', 'later')), 'ok');
await db.exec(`insert into essick_feedback (client_id, key, kind, name, ip_hash) select gen_random_uuid(), 'f' || g, 'answer', 'f', 'h' || g from generate_series(1, 600) g`);
assert.equal(await code(post('5.5.5.5', B, 'flood', 'answer', 'B')), 'PT429');
await db.exec(`delete from essick_feedback where name = 'f'`);
// kill switch and hidden
await db.exec(`update essick_settings set value = '0'`);
assert.equal(await code(post('4.4.4.4', B, 'x', 'comment', 'B', 'x')), 'PT403');
assert.equal((await list()).postingEnabled, false);
await db.exec(`update essick_settings set value = '1'; update essick_feedback set hidden = true where name = 'Old'`);
assert.ok(!(await list()).items.some(i => i.name === 'Old'));
// tables and helpers locked to the public key
for (const q of [`select * from essick_feedback`, `select * from essick_private`, `update essick_feedback set hidden = false`,
  `select essick_ip_hash()`, `select essick_clean('x')`])
  assert.equal(await code(as('1.1.1.1', q)), '42501', q);
// storage bucket and policy exist
assert.equal((await db.query(`select public from storage.buckets where id = 'essick-photos'`)).rows[0].public, true);
assert.equal((await db.query(`select count(*)::int n from pg_policies where tablename = 'objects'`)).rows[0].n, 1);
console.log('all feedback SQL checks pass');
