// Run: node --test comments-api/test   (Node 22.5+; uses the built-in node:sqlite as a stand-in for D1)
import {DatabaseSync} from 'node:sqlite';
import {readFileSync} from 'node:fs';
import {afterEach, describe, it} from 'node:test';
import assert from 'node:assert/strict';
import worker, {cleanText, LIMITS} from '../src/index.js';

const MIGRATION = new URL('../migrations/0001_comments.sql', import.meta.url);
const ORIGIN = 'https://masterminnich.github.io';

function createD1() {
  const db = new DatabaseSync(':memory:');
  const sql = readFileSync(MIGRATION, 'utf8');
  db.exec(sql);
  db.exec(sql); // the migration is safe to run twice
  const statement = (text, args = []) => ({
    bind: (...values) => statement(text, values),
    async first() { const row = db.prepare(text).get(...args); return row ? {...row} : null; },
    async all() { return {results: db.prepare(text).all(...args).map(r => ({...r}))}; },
    async run() { const r = db.prepare(text).run(...args); return {meta: {changes: Number(r.changes)}}; },
  });
  return {sqlite: db, prepare: text => statement(text)};
}

function setup(extraEnv = {}) {
  const env = {ESSICK_IP_SALT: 'test-salt', DB: createD1(), ...extraEnv};
  const call = (path, {method = 'GET', body, ip = '203.0.113.7', headers = {}} = {}) => worker.fetch(new Request('https://comments.test' + path, {
    method,
    headers: {'CF-Connecting-IP': ip, Origin: ORIGIN, ...(body !== undefined ? {'Content-Type': 'application/json'} : {}), ...headers},
    body: body === undefined ? undefined : (typeof body === 'string' ? body : JSON.stringify(body)),
  }), env);
  const post = (body, opts = {}) => call('/comments', {method: 'POST', body, ...opts});
  const setPosting = v => env.DB.sqlite.prepare("UPDATE essick_settings SET value = ? WHERE key = 'posting_enabled'").run(v);
  return {env, call, post, setPosting, rows: () => env.DB.sqlite.prepare('SELECT * FROM essick_comments').all()};
}

const realFetch = globalThis.fetch;
afterEach(() => { globalThis.fetch = realFetch; });

describe('ESSICK rocker comments', () => {
  it('saves a trimmed plain-text comment and lists visible comments oldest first without ip_hash', async () => {
    const {post, call, rows} = setup();
    const first = await post({name: '  Ada  ', body: ' Lovely joinery.\r\nWhat wood?\u0007 ', website: ''});
    assert.equal(first.status, 200);
    const {comment} = await first.json();
    assert.equal(comment.name, 'Ada');
    assert.equal(comment.body, 'Lovely joinery.\nWhat wood?');
    await post({name: 'Ben', body: '<b>not html</b>'});
    const list = await (await call('/comments')).json();
    assert.equal(list.postingEnabled, true);
    assert.deepEqual(list.comments.map(c => c.name), ['Ada', 'Ben']);
    assert.equal(list.comments[1].body, '<b>not html</b>');
    for (const c of list.comments) assert.deepEqual(Object.keys(c).sort(), ['body', 'created_at', 'id', 'name']);
    const stored = rows();
    assert.match(stored[0].ip_hash, /^[a-f0-9]{64}$/);
    assert.ok(!JSON.stringify(stored).includes('203.0.113.7'));
  });

  it('validates name and body lengths', async () => {
    const {post, rows} = setup();
    for (const body of [{name: '', body: 'x'}, {name: '   ', body: 'x'}, {name: 'x'.repeat(61), body: 'x'}, {name: 'A', body: ''}, {name: 'A', body: 'x'.repeat(2001)}, {name: 7, body: 'x'}, 'not json', '[]']) {
      assert.equal((await post(body)).status, 400, JSON.stringify(body));
    }
    assert.equal((await post({name: 'x'.repeat(60), body: 'y'.repeat(2000)})).status, 200);
    assert.equal((await post({name: 'A', body: 'x'.repeat(LIMITS.requestBytes)})).status, 413);
    assert.equal(rows().length, 1);
  });

  it('answers a filled honeypot as if saved but stores nothing', async () => {
    const {post, rows} = setup();
    const response = await post({name: 'Bot', body: 'Buy now', website: 'https://spam.test'});
    assert.equal(response.status, 200);
    const j = await response.json();
    assert.equal(j.ok, true);
    assert.equal(j.comment.body, 'Buy now');
    assert.equal(rows().length, 0);
  });

  it('allows 5 posts per visitor per 10 minutes, then 429', async () => {
    const {post, env} = setup();
    for (let i = 0; i < 5; i++) assert.equal((await post({name: 'A', body: `n${i}`})).status, 200);
    const limited = await post({name: 'A', body: 'sixth'});
    assert.equal(limited.status, 429);
    assert.equal(limited.headers.get('Retry-After'), '600');
    assert.equal((await post({name: 'B', body: 'other visitor'}, {ip: '198.51.100.1'})).status, 200);
    env.DB.sqlite.prepare("UPDATE essick_comments SET created_at = '2020-01-01T00:00:00.000Z'").run();
    assert.equal((await post({name: 'A', body: 'later'})).status, 200);
  });

  it('refuses posts when posting is turned off, and when the salt secret is missing', async () => {
    const {post, call, setPosting} = setup();
    setPosting('0');
    assert.equal((await post({name: 'A', body: 'x'})).status, 403);
    assert.equal((await (await call('/comments')).json()).postingEnabled, false);
    setPosting('1');
    assert.equal((await post({name: 'A', body: 'x'})).status, 200);
    assert.equal((await setup({ESSICK_IP_SALT: ''}).post({name: 'A', body: 'x'})).status, 503);
  });

  it('checks Turnstile only when TURNSTILE_SECRET is set', async () => {
    let calls = 0;
    globalThis.fetch = async (url, init) => {
      calls++;
      assert.equal(url, 'https://challenges.cloudflare.com/turnstile/v0/siteverify');
      assert.equal(init.body.get('secret'), 'ts-secret');
      assert.equal(init.body.get('remoteip'), '203.0.113.7');
      return Response.json({success: init.body.get('response') === 'good-token'});
    };
    const {post, rows} = setup({TURNSTILE_SECRET: 'ts-secret'});
    assert.equal((await post({name: 'A', body: 'x'})).status, 403);
    assert.equal((await post({name: 'A', body: 'x', turnstileToken: 'bad-token'})).status, 403);
    assert.equal((await post({name: 'A', body: 'x', turnstileToken: 'good-token'})).status, 200);
    assert.equal(calls, 2);
    assert.equal(rows().length, 1);
    calls = 0;
    assert.equal((await setup().post({name: 'A', body: 'x'})).status, 200);
    assert.equal(calls, 0);
  });

  it('hides hidden comments from the public list', async () => {
    const {post, call, env} = setup();
    const {comment} = await (await post({name: 'A', body: 'first'})).json();
    await post({name: 'B', body: 'second'});
    env.DB.sqlite.prepare('UPDATE essick_comments SET hidden = 1 WHERE id = ?').run(comment.id);
    assert.deepEqual((await (await call('/comments')).json()).comments.map(c => c.name), ['B']);
  });

  it('allows CORS only from the GitHub Pages site, answers preflight, and exposes nothing else', async () => {
    const {call} = setup();
    const pre = await call('/comments', {method: 'OPTIONS'});
    assert.equal(pre.status, 204);
    assert.equal(pre.headers.get('Access-Control-Allow-Origin'), ORIGIN);
    const evil = await call('/comments', {headers: {Origin: 'https://evil.test'}});
    assert.equal(evil.headers.get('Access-Control-Allow-Origin'), null);
    assert.equal((await call('/comments/admin')).status, 404);
    assert.equal((await call('/comments', {method: 'DELETE'})).status, 405);
  });

  it('keeps comments plain text', () => {
    assert.equal(cleanText('  a\r\nb‮c\u0000 '), 'a\nbc');
    assert.equal(cleanText(42), '');
  });
});
