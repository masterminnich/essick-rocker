// Rocker viewer server. No dependencies: `npm run dev` (PORT, HOST from the environment; default 127.0.0.1:8765).
//
// Serves viewer/ as static files, and the model files it finds:
//   GET /api/models        -> { latest, models: [{ id, file, version, mtime, size, dir }] }  newest first
//   GET /models/<id>       -> the .glb (no-store, so a reload always gets the current bytes)
// Model folders searched, in order: <repo>/parts, every line of viewer/model-dirs.local (git-ignored; e.g. the main
// worktree's parts/ folder, so the viewer shows a model the moment build_model.py writes it, before it is committed),
// and the paths in ESSICK_MODEL_DIRS (colon separated). "Latest" = highest vN; on a tie, the newest file.
import { createServer } from 'node:http'
import { readFileSync, existsSync, statSync, readdirSync, createReadStream } from 'node:fs'
import { join, resolve, extname, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const HERE = dirname(fileURLToPath(import.meta.url))
const REPO = resolve(HERE, '..')
const PORT = Number(process.env.PORT || 8765)
const HOST = process.env.HOST || '127.0.0.1'
const MODEL_RE = /^model_v(\d+)\.glb$/

function modelDirs() {
  const dirs = [join(REPO, 'parts')]
  const local = join(HERE, 'model-dirs.local')
  if (existsSync(local)) dirs.push(...readFileSync(local, 'utf8').split('\n').map(s => s.trim()).filter(s => s && !s.startsWith('#')))
  if (process.env.ESSICK_MODEL_DIRS) dirs.push(...process.env.ESSICK_MODEL_DIRS.split(':').filter(Boolean))
  return [...new Set(dirs.map(d => resolve(REPO, d)))]
}

function listModels() {
  const byFile = new Map()                         // same file name in two folders: keep the newer one
  modelDirs().forEach((dir, di) => {
    let names = []
    try { names = readdirSync(dir) } catch { return }
    for (const file of names) {
      const m = MODEL_RE.exec(file); if (!m) continue
      const st = statSync(join(dir, file))
      const rec = { id: `${di}-${file}`, file, version: Number(m[1]), mtime: st.mtimeMs, size: st.size, dir: di === 0 ? 'repo' : dir.split('/').slice(-2).join('/'), path: join(dir, file) }
      const prev = byFile.get(file)
      if (!prev || prev.mtime < rec.mtime) byFile.set(file, rec)
    }
  })
  const models = [...byFile.values()].sort((a, b) => b.version - a.version || b.mtime - a.mtime)
  return models
}

const TYPES = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.mjs': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8',
  '.json': 'application/json', '.jpg': 'image/jpeg', '.png': 'image/png', '.svg': 'image/svg+xml', '.glb': 'model/gltf-binary', '.woff2': 'font/woff2' }

function send(res, code, body, type = 'text/plain; charset=utf-8', extra = {}) {
  res.writeHead(code, { 'content-type': type, ...extra }); res.end(body)
}

function sendFile(res, path, cache) {
  const st = statSync(path)
  res.writeHead(200, { 'content-type': TYPES[extname(path)] || 'application/octet-stream', 'content-length': st.size, 'cache-control': cache })
  createReadStream(path).pipe(res)
}

createServer((req, res) => {
  const url = new URL(req.url, 'http://x')
  const p = decodeURIComponent(url.pathname)
  try {
    if (p === '/api/models') {
      const models = listModels()
      return send(res, 200, JSON.stringify({ latest: models[0]?.id ?? null, models: models.map(({ path, ...m }) => m) }), 'application/json', { 'cache-control': 'no-store' })
    }
    if (p.startsWith('/models/')) {
      const m = listModels().find(x => x.id === p.slice(8))
      return m ? sendFile(res, m.path, 'no-store') : send(res, 404, 'no such model')
    }
    const rel = p === '/' ? 'index.html' : p.slice(1)
    const path = resolve(HERE, rel)
    if (!path.startsWith(HERE + '/') || path.endsWith('.local') || !existsSync(path) || !statSync(path).isFile()) return send(res, 404, 'not found')
    return sendFile(res, path, rel.startsWith('photos/') ? 'public, max-age=86400' : 'no-cache')
  } catch (e) {
    return send(res, 500, String(e?.message || e))
  }
}).listen(PORT, HOST, () => console.log(`rocker viewer on http://${HOST}:${PORT}  (model folders: ${modelDirs().join(', ')})`))
