// ESSICK rocker comments: a public comment thread for one page only, the ESSICK rocker
// reconstruction at https://masterminnich.github.io/essick-rocker/ (static, no sign-in).
// Its own Worker and its own D1 database (essick-rocker-comments) in the Marcella
// Foundation Cloudflare account; it shares nothing with the Foundation's other data.
//
//   GET  /comments   visible comments, oldest first, never ip_hash; plus postingEnabled
//   POST /comments   {name, body, website, turnstileToken?}
//
// Safeguards on POST: a `website` honeypot (filled = pretend success, store nothing),
// length limits, at most 5 posts per visitor per 10 minutes (visitor = SHA-256 of
// CF-Connecting-IP + ESSICK_IP_SALT; raw IPs are never stored), a posting on/off switch,
// and Cloudflare Turnstile when TURNSTILE_SECRET is set. Moderation (hide, delete, close)
// has no web endpoint: it runs from GitHub Actions ("Moderate comments"). See README.md.
// No dependencies, so the deploy needs nothing but wrangler.

export const LIMITS = {name: 60, body: 2000, posts: 5, windowMs: 10 * 60 * 1000, requestBytes: 16 * 1024};
const SITEVERIFY = 'https://challenges.cloudflare.com/turnstile/v0/siteverify';
const ORIGINS = new Set(['https://masterminnich.github.io']);

// Plain text only: normalise newlines, drop control characters (keeping newline and tab)
// and bidi overrides, trim. Pages must render comments as text (textContent), never HTML.
export function cleanText(value) {
  if (typeof value !== 'string') return '';
  // eslint-disable-next-line no-control-regex
  return value.replace(/\r\n?/g, '\n').replace(/[\u0000-\u0008\u000B-\u001F\u007F​-‏‪-‮⁦-⁩]/g, '').trim();
}

async function sha256Hex(text) {
  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text));
  return [...new Uint8Array(digest)].map(b => b.toString(16).padStart(2, '0')).join('');
}

async function postingEnabled(env) {
  const row = await env.DB.prepare('SELECT value FROM essick_settings WHERE key = ?').bind('posting_enabled').first();
  return (row?.value ?? '1') !== '0';
}

async function verifyTurnstile(env, token, ip) {
  if (typeof token !== 'string' || !token || token.length > 2048) return false;
  const form = new FormData();
  form.append('secret', env.TURNSTILE_SECRET);
  form.append('response', token);
  if (ip) form.append('remoteip', ip);
  try {
    const response = await fetch(SITEVERIFY, {method: 'POST', body: form});
    const result = await response.json();
    return result?.success === true;
  } catch {
    return false;
  }
}

const publicShape = row => ({id: row.id, name: row.name, body: row.body, created_at: row.created_at});

function cors(request) {
  const origin = request.headers.get('Origin');
  const h = {Vary: 'Origin'};
  if (origin && ORIGINS.has(origin)) {
    h['Access-Control-Allow-Origin'] = origin;
    h['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS';
    h['Access-Control-Allow-Headers'] = 'Content-Type, Accept';
    h['Access-Control-Max-Age'] = '86400';
  }
  return h;
}

const json = (request, data, status = 200, extra = {}) => new Response(JSON.stringify(data), {
  status,
  headers: {'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff', ...cors(request), ...extra},
});
const fail = (request, status, message, extra) => json(request, {error: {message}}, status, extra);

async function list(request, env) {
  const {results} = await env.DB.prepare(
    'SELECT id, name, body, created_at FROM essick_comments WHERE hidden = 0 ORDER BY created_at ASC, id ASC LIMIT 1000'
  ).all();
  return json(request, {comments: results.map(publicShape), postingEnabled: await postingEnabled(env)});
}

async function create(request, env) {
  if (!env.ESSICK_IP_SALT) return fail(request, 503, 'Comments are not configured yet.');
  if (Number(request.headers.get('Content-Length')) > LIMITS.requestBytes) return fail(request, 413, 'That comment is too long.');
  const raw = await request.text();
  if (raw.length > LIMITS.requestBytes) return fail(request, 413, 'That comment is too long.');
  let input;
  try { input = JSON.parse(raw); } catch { return fail(request, 400, 'Send the comment as JSON.'); }
  if (!input || typeof input !== 'object') return fail(request, 400, 'Send the comment as JSON.');

  const name = cleanText(input.name);
  const body = cleanText(input.body);
  const comment = {id: crypto.randomUUID(), name, body, created_at: new Date().toISOString()};

  if (!name || name.length > LIMITS.name) return fail(request, 400, `Name must be 1 to ${LIMITS.name} characters.`);
  if (!body || body.length > LIMITS.body) return fail(request, 400, `Comment must be 1 to ${LIMITS.body} characters.`);

  // Honeypot: people never see the `website` field, so anything in it is a bot. Answer
  // exactly as a successful save would, and store nothing.
  if (typeof input.website === 'string' ? input.website.trim() : input.website) {
    return json(request, {ok: true, comment});
  }

  if (!await postingEnabled(env)) return fail(request, 403, 'Comments are closed for now.');

  const ip = request.headers.get('CF-Connecting-IP') || '';
  if (env.TURNSTILE_SECRET && !await verifyTurnstile(env, input.turnstileToken, ip)) {
    return fail(request, 403, 'The spam check did not pass. Reload the page and try again.');
  }

  const ipHash = await sha256Hex(`${ip || 'unknown'}|${env.ESSICK_IP_SALT}`);
  const since = new Date(Date.parse(comment.created_at) - LIMITS.windowMs).toISOString();
  const recent = await env.DB.prepare(
    'SELECT COUNT(*) AS n FROM essick_comments WHERE ip_hash = ? AND created_at > ?'
  ).bind(ipHash, since).first();
  if ((recent?.n ?? 0) >= LIMITS.posts) {
    return fail(request, 429, 'You have posted a lot in a short time. Please wait a few minutes.', {'Retry-After': String(LIMITS.windowMs / 1000)});
  }

  await env.DB.prepare(
    'INSERT INTO essick_comments (id, name, body, created_at, hidden, ip_hash) VALUES (?, ?, ?, ?, 0, ?)'
  ).bind(comment.id, comment.name, comment.body, comment.created_at, ipHash).run();
  return json(request, {ok: true, comment});
}

export default {
  async fetch(request, env) {
    const {pathname} = new URL(request.url);
    if (pathname === '/comments') {
      if (request.method === 'OPTIONS') return new Response(null, {status: 204, headers: cors(request)});
      try {
        if (request.method === 'GET') return await list(request, env);
        if (request.method === 'POST') return await create(request, env);
      } catch (err) {
        console.error('comments error', err?.stack || err);
        return fail(request, 500, 'Something went wrong. Try again in a moment.');
      }
      return fail(request, 405, 'Method not allowed.', {Allow: 'GET, POST, OPTIONS'});
    }
    if (pathname === '/' || pathname === '/health') return json(request, {ok: true, service: 'essick-rocker-comments'});
    return fail(request, 404, 'Not found.');
  },
};
