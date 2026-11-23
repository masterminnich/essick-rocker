# Comments service

The public comment thread on the viewer (`viewer/comments.js`). A small Cloudflare Worker
with its own D1 database, `essick-rocker-comments`, in the Marcella Foundation account.
It is deliberately separate from the Foundation's main database (feedtahoe): this repo is
public, so its code only ever touches its own comments.

- **Live at** <https://essick-rocker-comments.sean-b08.workers.dev/comments>
- **Goes live** by pushing to `main` (`.github/workflows/deploy-comments.yml`): tests, create
  the database if it is missing, apply `migrations/`, deploy, set the rate-limit salt once.
- **Needs** one repo secret, `CLOUDFLARE_API_TOKEN` (Marcella Foundation account,
  Workers Scripts: Edit + D1: Edit).
- **Test** `node --test comments-api/test/*.test.mjs` (Node 22.5+, no installs).

## API

| Method | Path | What |
|---|---|---|
| GET | `/comments` | `{comments: [{id, name, body, created_at}], postingEnabled}`, visible only, oldest first, at most 1000 |
| POST | `/comments` | `{name, body, website, turnstileToken?}` → `200 {ok, comment}` |

POST answers 400 (not JSON, name not 1–60 or body not 1–2000 characters), 403 (posting
closed, or Turnstile failed), 413 (over 16 KB), 429 (over 5 posts in 10 minutes,
`Retry-After: 600`), 503 (salt not set yet). CORS allows only `https://masterminnich.github.io`.

## Spam protection

- Plain text only: trimmed, control and bidi-override characters removed; the page renders
  with `textContent`.
- Honeypot: the hidden `website` field. Filled in = answered like a save, nothing stored.
- 5 posts per visitor per 10 minutes. Visitor = SHA-256 of their IP + the `ESSICK_IP_SALT`
  Worker secret; raw IPs are never stored or returned.
- Posting on/off switch (`essick_settings.posting_enabled`).
- Optional Turnstile: set the `TURNSTILE_SECRET` Worker secret and `TURNSTILE_SITE_KEY` in
  `viewer/comments.js` (page first, then the secret).

## Moderating

GitHub → Actions → **Moderate comments** → Run workflow: `list`, `hide`, `unhide`,
`delete` (with the comment id from `list`), `close posting`, `open posting`.
