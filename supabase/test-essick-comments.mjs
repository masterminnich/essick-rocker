// Checks essick-comments.sql in a real (in-memory) Postgres, acting as Supabase's public role.
// Run from a scratch folder: npm i @electric-sql/pglite && node <this file> <path to essick-comments.sql>
import {PGlite} from '@electric-sql/pglite';
import {readFileSync} from 'node:fs';
import assert from 'node:assert/strict';
const sql = readFileSync(process.argv[2], 'utf8');
const db = new PGlite();
await db.exec(`create role anon nologin; create role authenticated nologin; grant usage on schema public to anon, authenticated;`);
await db.exec(sql); await db.exec(sql); // twice: safe to re-run
const salt1 = (await db.query(`select value from essick_private`)).rows[0].value;
assert.match(salt1, /^[0-9a-f]{64}$/);
const as = async (ip, q, params = []) => {
  await db.exec(`reset role`);
  await db.query(`select set_config('request.headers', $1, false)`, [JSON.stringify({'cf-connecting-ip': ip})]);
  await db.exec(`set role anon`);
  try { return (await db.query(q, params)).rows; } finally { await db.exec(`reset role`); }
};
const post = (ip, n, b, w = '') => as(ip, `select essick_comment_post($1,$2,$3) as r`, [n, b, w]).then(r => r[0].r);
const code = async (p) => { try { await p; return 'ok'; } catch (e) { return e.code; } };
const list = (ip = '1.1.1.1') => as(ip, `select essick_comments_list() as r`).then(r => r[0].r);

// clean + save
let r = await post('203.0.113.7', '  Ada  ', ' Lovely joinery.\r\nWhat wood?\u0007‮ ');
assert.equal(r.comment.name, 'Ada'); assert.equal(r.comment.body, 'Lovely joinery.\nWhat wood?');
await post('203.0.113.7', 'Ben', '<b>not html</b>');
let l = await list();
assert.equal(l.postingEnabled, true);
assert.deepEqual(l.comments.map(c => c.name), ['Ada', 'Ben']);
assert.deepEqual(Object.keys(l.comments[0]).sort(), ['body', 'created_at', 'id', 'name']);
const stored = (await db.query(`select * from essick_comments`)).rows;
assert.match(stored[0].ip_hash, /^[0-9a-f]{64}$/); assert.ok(!JSON.stringify(stored).includes('203.0.113.7'));
// validation
for (const [n, b] of [['', 'x'], ['   ', 'x'], ['x'.repeat(61), 'x'], ['A', ''], ['A', 'x'.repeat(2001)], [null, 'x']]) assert.equal(await code(post('9.9.9.9', n, b)), 'PT400', JSON.stringify([n, b?.length]));
assert.equal((await post('9.9.9.9', 'x'.repeat(60), 'y'.repeat(2000))).ok, true);
// honeypot
const before = (await db.query(`select count(*)::int n from essick_comments`)).rows[0].n;
r = await post('8.8.8.8', 'Bot', 'Buy now', 'https://spam.test'); assert.equal(r.ok, true);
assert.equal((await db.query(`select count(*)::int n from essick_comments`)).rows[0].n, before);
// rate limit: 203.0.113.7 already has 2
for (let i = 0; i < 3; i++) assert.equal(await code(post('203.0.113.7', 'A', 'n' + i)), 'ok');
assert.equal(await code(post('203.0.113.7', 'A', 'sixth')), 'PT429');
assert.equal(await code(post('198.51.100.1', 'B', 'other')), 'ok');
await db.exec(`update essick_comments set created_at = now() - interval '1 hour'`);
assert.equal(await code(post('203.0.113.7', 'A', 'later')), 'ok');
// global cap 60 / 10 min
await db.exec(`insert into essick_comments (name, body, ip_hash) select 'f', 'f', 'h' || g from generate_series(1, 60) g`);
assert.equal(await code(post('7.7.7.7', 'A', 'flood')), 'PT429');
await db.exec(`delete from essick_comments where name = 'f'`);
// kill switch + hidden
await db.exec(`update essick_settings set value = '0'`);
assert.equal(await code(post('6.6.6.6', 'A', 'x')), 'PT403');
assert.equal((await list()).postingEnabled, false);
await db.exec(`update essick_settings set value = '1'`);
await db.exec(`update essick_comments set hidden = true where name = 'Ada'`);
assert.ok(!(await list()).comments.some(c => c.name === 'Ada'));
// tables locked to the public key
for (const q of [`select * from essick_comments`, `select * from essick_private`, `insert into essick_comments (name, body) values ('x','y')`, `update essick_settings set value='0'`, `select essick_clean('x')`])
  assert.equal(await code(as('1.1.1.1', q)), '42501', q);
console.log('all SQL checks pass');
