-- Migration: ESSICK rocker public comments
-- Comments for the ESSICK rocker reconstruction page (https://masterminnich.github.io/essick-rocker/).
-- Applies to the DB binding (its own D1 database, essick-rocker-comments).
-- The deploy workflow applies it (wrangler d1 migrations apply DB --remote).
-- Safe to run more than once. No IP addresses are stored: ip_hash is SHA-256 of the
-- visitor's IP plus the ESSICK_IP_SALT Worker secret, used only for rate limiting.

CREATE TABLE IF NOT EXISTS essick_comments (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  body TEXT NOT NULL,
  created_at TEXT NOT NULL,
  hidden INTEGER NOT NULL DEFAULT 0,
  ip_hash TEXT
);
CREATE INDEX IF NOT EXISTS essick_comments_created ON essick_comments(created_at);
CREATE INDEX IF NOT EXISTS essick_comments_ip_created ON essick_comments(ip_hash, created_at);

CREATE TABLE IF NOT EXISTS essick_settings (
  key TEXT PRIMARY KEY,
  value TEXT
);
INSERT OR IGNORE INTO essick_settings (key, value) VALUES ('posting_enabled', '1');
