// Saving for the review app. All feedback (comments, notes with pins and photos, size answers, "looks right") is
// SHARED: on the live site it goes to Supabase (supabase/essick-feedback.sql) and everyone sees everyone's.
// Anywhere else (the preview, a local copy) it is kept on this device only, so tests never touch the real feedback.
//
// A record, as the app sees it:
//   { id, type: 'comment' | 'note' | 'answer' | 'question' | 'part_ok', who, mine, at (ms), text, photos: [photoId], ...details }
// Your own records keep their id (for an answer it is `answer-<dimension id>`, so answering again replaces it).

// The URL and the publishable key are public by design: the database only lets that key call the feedback functions.
const SUPABASE_URL = 'https://cvfejlnfytsyswpkyamt.supabase.co'
const SUPABASE_KEY = 'sb_publishable_T53HgBKsth7uv4euw3vMpA_QyzO9se5'
const LIVE_HOSTS = ['masterminnich.github.io']
const BUCKET = 'essick-photos'
export const SHARED = LIVE_HOSTS.includes(location.hostname)

const NAME_KEY = 'er.comments.name', CLIENT_KEY = 'er.client'
const ls = { get: (k) => { try { return localStorage.getItem(k) } catch { return null } }, set: (k, v) => { try { localStorage.setItem(k, v) } catch {} } }
export const getName = () => ls.get(NAME_KEY) || ''
export const setName = (n) => ls.set(NAME_KEY, String(n || '').trim().slice(0, 60))
function client() {
  let c = ls.get(CLIENT_KEY)
  if (!/^[0-9a-f-]{36}$/.test(c || '')) { c = crypto.randomUUID(); ls.set(CLIENT_KEY, c) }
  return c
}
export const newId = (p) => `${p}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 7)}`
export const state = { postingEnabled: true, loadError: false }

// An error the page can show as it is: .status 403 = closed, 429 = slow down.
class SaveError extends Error { constructor(status, msg) { super(msg); this.status = status } }

// ------------------------------------------------------------------ shared (Supabase)
async function rpc(fn, args) {
  const ctl = new AbortController(); const t = setTimeout(() => ctl.abort(), 12000)
  try {
    const r = await fetch(`${SUPABASE_URL}/rest/v1/rpc/${fn}`, {
      method: 'POST', signal: ctl.signal, body: JSON.stringify(args || {}),
      headers: { apikey: SUPABASE_KEY, 'content-type': 'application/json', accept: 'application/json' },
    })
    const j = await r.json().catch(() => null)
    if (!r.ok) throw new SaveError(r.status, (r.status === 400 && j?.code === 'PT400' && j.message) || '')
    return j
  } catch (e) {
    if (e instanceof SaveError) throw e
    throw new SaveError(0, 'Could not reach the server. Check your connection and try again.')
  } finally { clearTimeout(t) }
}
const safeKey = (k) => String(k).replace(/[^A-Za-z0-9_.-]/g, '_').slice(0, 80)
const DETAIL_SKIP = new Set(['id', 'type', 'who', 'mine', 'at', 'updated', 'text', 'body', 'synced', 'n'])
function fromServer(i) {
  return { ...(i.data || {}), id: i.mine ? i.key : i.id, type: i.kind, who: i.name, mine: !!i.mine, text: i.body || '',
    at: Date.parse(i.created_at), updated: Date.parse(i.updated_at), photos: i.data?.photos || [] }
}
const remote = {
  async all() {
    const j = await rpc('essick_feedback_list', { p_client: client() })
    state.postingEnabled = j?.postingEnabled !== false
    return (j?.items || []).map(fromServer)
  },
  async save(rec, photos) {
    for (const p of photos) {
      const r = await fetch(`${SUPABASE_URL}/storage/v1/object/${BUCKET}/${p.id}`, {
        method: 'POST', body: p.blob, headers: { apikey: SUPABASE_KEY, 'content-type': 'image/jpeg', 'x-upsert': 'false' },
      }).catch(() => null)
      if (!r || !r.ok) throw new SaveError(r?.status === 429 ? 429 : 0, 'A photo did not upload. Try again, or save without it.')
    }
    const data = {}; for (const [k, v] of Object.entries(rec)) if (!DETAIL_SKIP.has(k) && v != null) data[k] = v
    const j = await rpc('essick_feedback_post', { p_client: client(), p_key: safeKey(rec.id), p_kind: rec.type, p_name: rec.who,
      p_body: rec.text || '', p_data: data, p_website: rec.website || '' })
    return fromServer(j.item)
  },
  async remove(id) { await rpc('essick_feedback_delete', { p_client: client(), p_key: safeKey(id) }) },
  async photoURL(id) { return `${SUPABASE_URL}/storage/v1/object/public/${BUCKET}/${encodeURIComponent(id)}` },
}

// ------------------------------------------------------------------ this device only (preview and local copies)
const DB = 'essick-rocker-review', STORE = 'records', PHOTOS = 'photos'
let dbp = null
function db() {
  if (!dbp) dbp = new Promise((res, rej) => {
    const r = indexedDB.open(DB, 1)
    r.onupgradeneeded = () => {
      const d = r.result
      if (!d.objectStoreNames.contains(STORE)) d.createObjectStore(STORE, { keyPath: 'id' })
      if (!d.objectStoreNames.contains(PHOTOS)) d.createObjectStore(PHOTOS, { keyPath: 'id' })
    }
    r.onsuccess = () => res(r.result); r.onerror = () => rej(r.error)
  })
  return dbp
}
async function tx(store, mode, fn) {
  const d = await db()
  return new Promise((res, rej) => {
    const t = d.transaction(store, mode); const s = t.objectStore(store); let out
    Promise.resolve(fn(s)).then((v) => { out = v })
    t.oncomplete = () => res(out); t.onerror = () => rej(t.error); t.onabort = () => rej(t.error)
  })
}
const req = (r) => new Promise((res, rej) => { r.onsuccess = () => res(r.result); r.onerror = () => rej(r.error) })
const urls = new Map()
const local = {
  async all() { return ((await tx(STORE, 'readonly', (s) => req(s.getAll()))) || []).map((r) => ({ who: getName() || 'You', ...r, mine: true })) },
  async save(rec, photos) {
    for (const p of photos) await tx(PHOTOS, 'readwrite', (s) => s.put({ id: p.id, blob: p.blob }))
    const old = await tx(STORE, 'readonly', (s) => req(s.get(rec.id)))
    const { website, ...clean } = rec
    const out = { ...clean, at: old?.at || Date.now(), updated: Date.now() }
    await tx(STORE, 'readwrite', (s) => s.put(out))
    return { ...out, mine: true }
  },
  async remove(id) {
    const rec = await tx(STORE, 'readonly', (s) => req(s.get(id)))
    await tx(STORE, 'readwrite', (s) => s.delete(id))
    for (const p of rec?.photos || []) await tx(PHOTOS, 'readwrite', (s) => s.delete(p))
  },
  async photoURL(id) {
    if (urls.has(id)) return urls.get(id)
    const p = await tx(PHOTOS, 'readonly', (s) => req(s.get(id))); if (!p) return null
    const u = URL.createObjectURL(p.blob); urls.set(id, u); return u
  },
}

const B = SHARED ? remote : local

// ------------------------------------------------------------------ what the app calls
// Everyone's records, oldest first; notes numbered 1, 2, 3 in that order (the pin numbers everyone sees).
export async function all() {
  try {
    const rows = (await B.all()).sort((a, b) => a.at - b.at)
    let n = 0; for (const r of rows) if (r.type === 'note') r.n = ++n
    state.loadError = false
    return rows
  } catch (e) { state.loadError = true; throw e }
}
// rec needs id, type and who. photos: [{ id, blob }] from preparePhoto, uploaded now (so a cancelled note leaves nothing).
export async function save(rec, photos = []) {
  if (!state.postingEnabled) throw new SaveError(403, 'Feedback is closed for now.')
  return B.save({ ...rec, photos: photos.map((p) => p.id) }, photos)
}
export const remove = (id) => B.remove(id)
export const photoURL = (id) => B.photoURL(id)

// Photos: downscaled on the device to about 1600 px on the long side, JPEG. Nothing is stored until the note is saved.
export async function preparePhoto(file, maxSide = 1600) {
  const bmp = await (window.createImageBitmap ? createImageBitmap(file, { imageOrientation: 'from-image' }) : loadImg(file))
  const k = Math.min(1, maxSide / Math.max(bmp.width, bmp.height))
  const c = document.createElement('canvas'); c.width = Math.round(bmp.width * k); c.height = Math.round(bmp.height * k)
  c.getContext('2d').drawImage(bmp, 0, 0, c.width, c.height)
  const blob = await new Promise((r) => c.toBlob(r, 'image/jpeg', 0.84))
  return { id: `${crypto.randomUUID()}.jpg`, blob, url: URL.createObjectURL(blob) }
}
function loadImg(file) {
  return new Promise((res, rej) => { const i = new Image(); i.onload = () => res(i); i.onerror = rej; i.src = URL.createObjectURL(file) })
}
